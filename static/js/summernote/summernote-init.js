// Summernote initialization for blog post forms
// Enterprise Edition - No debug logs in production
$(document).ready(function() {
    const DEBUG = window.DEBUG || false;
    const log = (msg) => DEBUG && console.log(msg);
    
    log('jQuery loaded: ' + (typeof jQuery !== 'undefined'));
    log('Summernote loaded: ' + (typeof $.fn.summernote !== 'undefined'));
    log('Body textarea exists: ' + ($('#id_body').length > 0));
    log('Summary textarea exists: ' + ($('#id_summary').length > 0));
    
    // Initialize Summernote on body field
    if ($('#id_body').length > 0) {
        $('#id_body').summernote({
            height: 400,
            focus: false,
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'strikethrough', 'superscript', 'subscript', 'clear']],
                ['fontname', ['fontname']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['height', ['height']],
                ['table', ['table']],
                ['insert', ['link', 'picture', 'video', 'hr']],
                ['view', ['fullscreen', 'codeview', 'help']]
            ],
            callbacks: {
                onInit: function() {
                    log('✓ Summernote body editor initialized successfully');
                },
                onError: function(e) {
                    console.error('Summernote body error:', e);
                }
            }
        });
    }
    
    // Initialize Summernote on summary field (simple version without toolbar)
    if ($('#id_summary').length > 0) {
        $('#id_summary').summernote({
            height: 150,
            focus: false,
            toolbar: [],  // No toolbar for summary
            disableDragAndDrop: true,
            callbacks: {
                onInit: function() {
                    log('✓ Summernote summary editor initialized successfully');
                },
                onError: function(e) {
                    console.error('Summernote summary error:', e);
                }
            }
        });
    }
    
    // Ensure content is synced on form submit
    $('form').on('submit', function() {
        if ($('#id_body').summernote) {
            $('#id_body').val($('#id_body').summernote('code'));
        }
        if ($('#id_summary').summernote) {
            $('#id_summary').val($('#id_summary').summernote('code'));
        }
    });
});
