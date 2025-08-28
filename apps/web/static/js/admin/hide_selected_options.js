(function($) {
    $(document).ready(function() {
        // Find all select elements for permission field
        var permissionSelects = $('select[name$="permission"]');

        function updateOptions() {
            var selectedPermissions = [];
            // Get all currently selected permissions
            permissionSelects.each(function() {
                if ($(this).val()) {
                    selectedPermissions.push($(this).val());
                }
            });

            // Iterate through each select to hide selected options
            permissionSelects.each(function() {
                var currentSelect = $(this);
                currentSelect.find('option').each(function() {
                    var optionValue = $(this).val();
                    // If the option is selected in another select, hide it.
                    if (selectedPermissions.includes(optionValue) && optionValue !== currentSelect.val()) {
                        $(this).hide();
                    } else {
                        $(this).show();
                    }
                });
            });
        }
        
        // Run on page load
        updateOptions();

        // Run when any select's value changes
        permissionSelects.change(updateOptions);

        // Also run when a new inline form is added
        // The '.add-row' class is a common Django Admin convention
        $('.add-row').click(function() {
            // Wait for the new form to be added to the DOM before updating
            setTimeout(updateOptions, 100);
        });
    });
})(django.jQuery);