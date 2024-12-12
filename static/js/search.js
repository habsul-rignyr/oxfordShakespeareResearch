document.addEventListener('DOMContentLoaded', function() {
    // Advanced Search Toggle
    const advancedToggle = document.querySelector('.advanced-toggle');
    const advancedSearch = document.getElementById('advancedSearch');

    if (advancedToggle && advancedSearch) {
        const toggleIcon = advancedToggle.querySelector('.toggle-icon');

        advancedToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            advancedSearch.classList.toggle('visible');
            const isVisible = advancedSearch.classList.contains('visible');
            toggleIcon.textContent = isVisible ? '▾' : '▸';
        });

        // Check URL parameters for advanced search fields
        const urlParams = new URLSearchParams(window.location.search);
        const hasAdvancedParams = ['must_have', 'should_have', 'must_not', 'phrase'].some(
            param => urlParams.has(param) && urlParams.get(param).trim() !== ''
        );

        if (hasAdvancedParams) {
            advancedSearch.classList.add('visible');
            toggleIcon.textContent = '▾';
        }
    }
});


    document.addEventListener('DOMContentLoaded', function() {
    // Keep your existing advanced search toggle code here

    // Sort Dropdown Functionality
    const sortToggle = document.getElementById('sortDropdownToggle');
    const sortOptions = document.getElementById('sortDropdownOptions');
    const sortInput = document.getElementById('sortInput');

    if (sortToggle && sortOptions && sortInput) {
        // Set initial text based on URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const currentSort = urlParams.get('sort');
        if (currentSort) {
            const selectedOption = sortOptions.querySelector(`[data-value="${currentSort}"]`);
            if (selectedOption) {
                sortToggle.textContent = selectedOption.textContent;
            }
        }

        // Toggle dropdown
        sortToggle.addEventListener('click', (e) => {
            e.preventDefault();
            sortOptions.classList.toggle('visible');
        });

        // Handle option selection
        sortOptions.addEventListener('click', (e) => {
            if (e.target.tagName === 'LI') {
                // Update button text before submitting
                sortToggle.textContent = e.target.textContent;
                sortInput.value = e.target.getAttribute('data-value');
                sortOptions.classList.remove('visible');
                document.getElementById('searchForm').submit();
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!sortToggle.contains(e.target) && !sortOptions.contains(e.target)) {
                sortOptions.classList.remove('visible');
            }
        });
    }
});