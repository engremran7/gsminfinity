from __future__ import annotations

from django.conf import settings
from django.db import models
from solo.models import SingletonModel


class AISettings(SingletonModel):
    """
    Global configuration singleton for the AI platform features.

    AISettings is a singleton model (only one instance ever exists) that manages
    global AI feature toggles, default model configuration, and safety/security settings.
    This allows the AI app to be decentralized (independently configured in each
    service while maintaining global consistency).

    Access via: AISettings.objects.get_solo()

    Attributes:
        ai_enabled (BooleanField): Master switch to enable/disable all AI features.
        default_model (CharField): Default LLM model identifier (e.g., "deepseek-chat").
            Used as fallback when specific model not requested.
        enable_vector_search (BooleanField): Enable semantic/vector search capabilities.
        enable_auto_translation (BooleanField): Enable automatic content translation.
        enable_safety_firewall (BooleanField): Enable content safety checks before/after
            generation (validates for harmful content, profanity, PII).
        default_locale (CharField): Default language/locale for responses (e.g., "en", "es").
        provider (CharField): Default AI service provider (e.g., "deepseek", "openai").
        base_url (URLField): API endpoint base URL for provider. Can override for
            self-hosted or proxy scenarios.
        api_key (TextField): API authentication key. Should use environment variables
            in production, not store directly.
        model_name (CharField): Explicit model name (may differ from default_model).
        timeout_seconds (PositiveIntegerField): Request timeout for API calls (default 30s).
        max_tokens (PositiveIntegerField): Maximum tokens in response generation.
        temperature (DecimalField): Model randomness (0.0=deterministic, 1.0=creative).
        log_prompts (BooleanField): Log all prompts sent to model (for debugging/audit).
        log_completions (BooleanField): Log all model completions (may include PII).
        pii_redaction_enabled (BooleanField): Automatically redact PII from prompts
            before sending to model.
        moderation_enabled (BooleanField): Check content safety before serving.
        allow_tools (BooleanField): Enable function calling / tool use in models.
        retry_limit (PositiveSmallIntegerField): Max retries on transient failures.
        backoff_min_seconds (FloatField): Minimum delay between retries (exponential backoff).
        backoff_max_seconds (FloatField): Maximum delay between retries (exponential backoff cap).

    Examples:
        >>> # Get singleton settings
        >>> settings = AISettings.objects.get_solo()
        >>>
        >>> # Check if AI features are enabled
        >>> if settings.ai_enabled:
        ...     llm = initialize_llm(
        ...         model=settings.default_model,
        ...         temperature=settings.temperature,
        ...         max_tokens=settings.max_tokens
        ...     )
        >>>
        >>> # Update global settings
        >>> settings.temperature = 0.7
        >>> settings.log_prompts = True
        >>> settings.save()
    """

    ai_enabled = models.BooleanField(default=True)
    default_model = models.CharField(max_length=100, default="deepseek-chat")
    enable_vector_search = models.BooleanField(default=True)
    enable_auto_translation = models.BooleanField(default=True)
    enable_safety_firewall = models.BooleanField(default=True)
    default_locale = models.CharField(max_length=16, default="en")
    provider = models.CharField(max_length=50, default="deepseek")
    base_url = models.URLField(blank=True, default="")
    api_key = models.TextField(blank=True, default="")
    model_name = models.CharField(max_length=100, default="deepseek-chat")
    timeout_seconds = models.PositiveIntegerField(default=30)
    max_tokens = models.PositiveIntegerField(default=1024)
    temperature = models.DecimalField(max_digits=3, decimal_places=2, default=0.30)
    log_prompts = models.BooleanField(default=False)
    log_completions = models.BooleanField(default=False)
    pii_redaction_enabled = models.BooleanField(default=True)
    moderation_enabled = models.BooleanField(default=True)
    allow_tools = models.BooleanField(default=False)
    retry_limit = models.PositiveSmallIntegerField(default=3)
    backoff_min_seconds = models.FloatField(default=0.5)
    backoff_max_seconds = models.FloatField(default=4.0)

    class Meta:
        verbose_name = "AI Settings"

    def __str__(self) -> str:
        return "AI Settings"


class ModelEndpoint(models.Model):
    """
    Represents a registered AI model endpoint (LLM, embedding, vision, etc.).

    ModelEndpoint stores configurations for external AI service connections. This
    allows the system to support multiple providers, models, and capabilities
    (text generation, embeddings, vision processing, speech). Endpoints can be
    enabled/disabled without deletion for audit trail.

    Typical use cases:
    - Register multiple LLM providers for fallback/comparison
    - Store separate embedding model for vector search
    - Register vision model for image analysis
    - Support self-hosted model endpoints via custom base URL

    Attributes:
        name (CharField): Unique identifier for this endpoint (e.g., "openai-gpt4", "local-llama2").
        kind (CharField): Type of endpoint - llm (text generation), embedding (vectors),
            vision (image analysis), or speech (audio processing).
        provider (CharField): AI service provider name (e.g., "openai", "deepseek", "anthropic",
            "custom" for self-hosted).
        endpoint (URLField): Full API endpoint URL. For custom/self-hosted, include the
            complete path (e.g., "http://localhost:8000/v1/completions").
        api_key (CharField): API authentication key. Should use environment variables
            in production. May be blank for local/unauthenticated endpoints.
        metadata (JSONField): Additional endpoint-specific configuration.
            Example: {"model": "gpt-4", "context_window": 8192, "cost_per_1k": 0.03}
        is_active (BooleanField): Whether this endpoint is available for use.
            Disabled endpoints won't be selected for new requests (for maintenance).
        created_at (DateTimeField): When this endpoint registration was created.
        updated_at (DateTimeField): When this endpoint was last updated.

    Examples:
        >>> # Register OpenAI as LLM provider
        >>> openai_endpoint = ModelEndpoint.objects.create(
        ...     name="openai-gpt4",
        ...     kind="llm",
        ...     provider="openai",
        ...     endpoint="https://api.openai.com/v1/chat/completions",
        ...     api_key=os.getenv("OPENAI_API_KEY"),
        ...     metadata={
        ...         "model": "gpt-4",
        ...         "context_window": 8192,
        ...         "cost_per_1k_tokens": 0.03
        ...     }
        ... )
        >>>
        >>> # Register local embedding model
        >>> embedding_endpoint = ModelEndpoint.objects.create(
        ...     name="local-embedding",
        ...     kind="embedding",
        ...     provider="custom",
        ...     endpoint="http://localhost:8000/embeddings",
        ...     metadata={
        ...         "model": "sentence-transformers/all-MiniLM-L6-v2",
        ...         "dimension": 384
        ...     }
        ... )
        >>>
        >>> # Get all active LLM endpoints
        >>> llm_providers = ModelEndpoint.objects.filter(
        ...     kind="llm",
        ...     is_active=True
        ... )
    """

    KIND_CHOICES = [
        ("llm", "LLM"),
        ("embedding", "Embedding"),
        ("vision", "Vision"),
        ("speech", "Speech"),
    ]

    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="llm")
    provider = models.CharField(max_length=100)
    endpoint = models.URLField()
    api_key = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"


class KnowledgeSource(models.Model):
    """
    Represents a knowledge base source for RAG (Retrieval-Augmented Generation).

    KnowledgeSource defines where content comes from that can be augmented into
    LLM prompts via vector search or knowledge retrieval. This supports various
    source types: uploaded files, web URLs, databases, or log streams. Each source
    tracks indexing state for incremental updates.

    Typical RAG workflow:
    1. Register KnowledgeSource (file, URL, DB)
    2. Content is indexed/embedded into vector database
    3. When user queries, system retrieves relevant chunks from source
    4. Augmented prompt = user query + relevant source context
    5. LLM generates response using context

    Attributes:
        name (CharField): Human-readable source name (e.g., "API Documentation", "Blog Posts").
        source_type (CharField): Type of source - file (PDF, doc), url (web page),
            db (database query), or log (streaming/log source).
        location (TextField): Source location specifier:
            - file: /path/to/file.pdf or S3://bucket/path
            - url: https://example.com/docs
            - db: postgresql://host/dbname;table=articles
            - log: kafka://topic or syslog://host:514
        metadata (JSONField): Source-specific configuration.
            For files: {"file_type": "pdf", "pages": [1, 2, 3]}
            For URLs: {"include_patterns": ["*.html"], "exclude_patterns": ["*.css"]}
            For DB: {"table": "articles", "content_field": "body", "metadata_fields": [...]}
            For logs: {"parser": "json", "timestamp_field": "timestamp"}
        last_indexed_at (DateTimeField): When this source was last indexed/updated.
            null = never indexed. Used for incremental re-indexing.
        is_active (BooleanField): Whether this source is included in RAG search.
            Can disable without deletion for quick A/B testing.
        created_at (DateTimeField): When this source was registered.

    Examples:
        >>> # Register PDF documentation
        >>> pdf_source = KnowledgeSource.objects.create(
        ...     name="API Reference Docs",
        ...     source_type="file",
        ...     location="s3://docs-bucket/api-ref.pdf",
        ...     metadata={
        ...         "file_type": "pdf",
        ...         "content_type": "documentation",
        ...         "update_frequency": "weekly"
        ...     }
        ... )
        >>>
        >>> # Register web documentation
        >>> web_source = KnowledgeSource.objects.create(
        ...     name="Django Docs",
        ...     source_type="url",
        ...     location="https://docs.djangoproject.com/",
        ...     metadata={
        ...         "include_patterns": ["/en/stable/*"],
        ...         "exclude_patterns": ["/en/dev/*"],
        ...         "crawl_depth": 5
        ...     }
        ... )
        >>>
        >>> # Register database table as knowledge source
        >>> db_source = KnowledgeSource.objects.create(
        ...     name="FAQ Database",
        ...     source_type="db",
        ...     location="postgresql://db.example.com/content;table=faqs",
        ...     metadata={
        ...         "table": "faqs",
        ...         "content_field": "answer",
        ...         "metadata_fields": ["category", "tags"],
        ...         "query_filter": "is_published=true"
        ...     }
        ... )
        >>>
        >>> # Check if source needs re-indexing (e.g., weekly)
        >>> from django.utils import timezone
        >>> from datetime import timedelta
        >>> seven_days_ago = timezone.now() - timedelta(days=7)
        >>> sources_needing_reindex = KnowledgeSource.objects.filter(
        ...     Q(last_indexed_at__lt=seven_days_ago) | Q(last_indexed_at__isnull=True),
        ...     is_active=True
        ... )
    """

    SOURCE_CHOICES = [
        ("file", "File"),
        ("url", "URL"),
        ("db", "Database"),
        ("log", "Log Stream"),
    ]

    name = models.CharField(max_length=150)
    source_type = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="file"
    )
    location = models.TextField(help_text="URI/path/connection string")
    metadata = models.JSONField(default=dict, blank=True)
    last_indexed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Workflow(models.Model):
    """
    Represents a declarative AI pipeline/workflow definition.

    Workflow defines a reusable sequence of AI operations (prompts, tool calls,
    conditional logic, etc.) in a declarative format. Rather than hardcoding
    AI logic in Python, workflows can be defined as JSON/YAML and modified
    without code changes.

    Typical workflow structure (as JSON):
    ```json
    {
        "steps": [
            {
                "id": "extract_intent",
                "type": "prompt",
                "template": "What is the user intent? {user_input}",
                "model": "gpt4"
            },
            {
                "id": "route",
                "type": "conditional",
                "switch": "{extract_intent.output}",
                "cases": {
                    "question": "step_answer_question",
                    "task": "step_create_task"
                }
            },
            {
                "id": "answer_question",
                "type": "prompt",
                "template": "Answer this question: {user_input}",
                "model": "gpt4"
            }
        ]
    }
    ```

    Workflows support:
    - Sequential steps with inputs/outputs
    - Conditional branching based on step results
    - Tool/function calling
    - Retry logic
    - Human-in-the-loop approval points

    Attributes:
        name (CharField): Unique workflow identifier (e.g., "email-classification",
            "customer-support-route").
        description (TextField): Human-readable purpose and documentation.
        definition (JSONField): Declarative workflow structure (JSON/YAML format).
            See apps.ai.workflows for schema documentation.
        is_active (BooleanField): Whether this workflow is available for execution.
            Disabled workflows won't start new runs.
        created_at (DateTimeField): When this workflow was first created.
        updated_at (DateTimeField): When this workflow definition was last modified.

    Examples:
        >>> # Create a simple workflow
        >>> workflow = Workflow.objects.create(
        ...     name="content-analysis",
        ...     description="Analyze user content for topics and sentiment",
        ...     definition={
        ...         "steps": [
        ...             {
        ...                 "id": "extract_topics",
        ...                 "type": "prompt",
        ...                 "prompt": "Extract main topics from: {content}",
        ...                 "model": "default"
        ...             },
        ...             {
        ...                 "id": "analyze_sentiment",
        ...                 "type": "prompt",
        ...                 "prompt": "Analyze sentiment: {content}",
        ...                 "model": "default"
        ...             }
        ...         ]
        ...     }
        ... )
        >>>
        >>> # Execute the workflow
        >>> run = PipelineRun.objects.create(
        ...     workflow=workflow,
        ...     requested_by=user,
        ...     input_payload={"content": "This product is amazing!"}
        ... )
        >>> # Executor processes the workflow definition and updates run.output_payload
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, default="")
    definition = models.JSONField(
        default=dict, blank=True, help_text="Declarative steps, tools, routing rules."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PipelineRun(models.Model):
    """
    Represents a single execution/run of a workflow or AI agent.

    PipelineRun is the execution log entry for workflow invocations. Each run
    tracks the input, output, status, timing, and metadata for audit trail,
    debugging, and monitoring purposes.

    Typical lifecycle:
    1. Created in "queued" status with input_payload
    2. Worker picks up run and changes status to "running"
    3. Executes workflow steps, updates metadata with progress
    4. On success: output_payload populated, status="succeeded", finished_at set
    5. On failure: status="failed", error info in metadata, finished_at set

    Runs can be filtered by status for dashboards, errors can be reviewed,
    and successful runs can be archived to archival storage.

    Attributes:
        workflow (ForeignKey): The Workflow being executed. Nullable to support
            one-off runs without a template. Related name: runs.
        requested_by (ForeignKey): The user who initiated this run. Nullable for
            system-initiated runs (scheduled, triggered by webhooks). Related name: ai_runs.
        input_payload (JSONField): Input data for this workflow run. Structure
            depends on specific workflow (documented in Workflow.definition).
            Example: {"user_input": "...", "context": {...}}
        output_payload (JSONField): Result of the workflow execution. Structure
            depends on workflow output schema. Example: {"classification": "...", "confidence": 0.95}
        status (CharField): Execution status - queued (waiting), running (in progress),
            succeeded (completed successfully), failed (error occurred).
        started_at (DateTimeField): When this run was created (automatically set).
        finished_at (DateTimeField): When execution completed (null until done).
        metadata (JSONField): Auxiliary execution data:
            - For running: {"progress": 0.5, "current_step": "extract_intent", "logs": [...]}
            - For failed: {"error": "...", "error_type": "...", "stack_trace": "..."}
            - For success: {"duration_seconds": 12.5, "tokens_used": 450}

    Meta:
        ordering: Most recent runs first
        indexes: On status and started_at for efficient filtering

    Examples:
        >>> from django.utils import timezone
        >>> from datetime import timedelta
        >>>
        >>> # Queue a new workflow run
        >>> workflow = Workflow.objects.get(name="email-classification")
        >>> run = PipelineRun.objects.create(
        ...     workflow=workflow,
        ...     requested_by=user,
        ...     input_payload={
        ...         "email_subject": "Limited time offer",
        ...         "email_body": "Get 50% off this week..."
        ...     }
        ... )
        >>> # Status is "queued" by default
        >>>
        >>> # Worker processes run
        >>> run.status = "running"
        >>> run.metadata = {"current_step": "extract_features", "progress": 0.2}
        >>> run.save()
        >>>
        >>> # Workflow completes successfully
        >>> run.status = "succeeded"
        >>> run.finished_at = timezone.now()
        >>> run.output_payload = {
        ...     "classification": "promotional",
        ...     "confidence": 0.98,
        ...     "tags": ["marketing", "limited-time"]
        ... }
        >>> run.metadata = {
        ...     "duration_seconds": 2.3,
        ...     "tokens_used": {"prompt": 150, "completion": 45}
        ... }
        >>> run.save()
        >>>
        >>> # Find failed runs from last hour for debugging
        >>> one_hour_ago = timezone.now() - timedelta(hours=1)
        >>> failed_runs = PipelineRun.objects.filter(
        ...     status="failed",
        ...     started_at__gte=one_hour_ago
        ... ).order_by("-started_at")
        >>> for run in failed_runs:
        ...     print(f"Run {run.pk}: {run.metadata.get('error')}")
        >>>
        >>> # Get average run duration for a workflow
        >>> from django.db.models import Avg, Q
        >>> avg_duration = PipelineRun.objects.filter(
        ...     workflow__name="email-classification",
        ...     status="succeeded"
        ... ).aggregate(
        ...     avg_seconds=Avg(
        ...         F("metadata__duration_seconds")
        ...     )
        ... )
    """

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
    ]

    workflow = models.ForeignKey(
        Workflow, null=True, blank=True, on_delete=models.SET_NULL, related_name="runs"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["status"], name="ai_pipeline_status_idx"),
            models.Index(fields=["started_at"], name="ai_pipeline_started_idx"),
        ]

    def __str__(self) -> str:
        return f"Run {self.pk} ({self.status})"
