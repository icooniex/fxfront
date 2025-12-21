// Custom Select Dropdown for Mobile
class CustomSelect {
    constructor(selectElement) {
        this.select = selectElement;
        this.options = Array.from(this.select.options);
        this.selectedIndex = this.select.selectedIndex;
        
        this.createCustomSelect();
        this.addEventListeners();
    }
    
    createCustomSelect() {
        // Create wrapper
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'custom-select-wrapper';
        
        // Create trigger button
        this.trigger = document.createElement('div');
        this.trigger.className = 'custom-select-trigger';
        this.trigger.innerHTML = `
            <span class="custom-select-value">${this.options[this.selectedIndex].text}</span>
            <i class="bi bi-chevron-down"></i>
        `;
        
        // Create options list
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'custom-select-dropdown';
        
        this.options.forEach((option, index) => {
            const optionElement = document.createElement('div');
            optionElement.className = 'custom-select-option';
            if (index === this.selectedIndex) {
                optionElement.classList.add('selected');
            }
            optionElement.textContent = option.text;
            optionElement.dataset.value = option.value;
            optionElement.dataset.index = index;
            this.dropdown.appendChild(optionElement);
        });
        
        // Only append trigger to wrapper (dropdown will be appended to body when opened)
        this.wrapper.appendChild(this.trigger);
        
        // Hide original select
        this.select.style.display = 'none';
        this.select.parentNode.insertBefore(this.wrapper, this.select);
    }
    
    addEventListeners() {
        // Toggle dropdown
        this.trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });
        
        // Select option
        this.dropdown.querySelectorAll('.custom-select-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectOption(option);
            });
        });
        
        // Close on outside click
        document.addEventListener('click', () => {
            this.closeDropdown();
        });
        
        // Reposition on scroll
        window.addEventListener('scroll', () => {
            if (this.wrapper.classList.contains('open')) {
                this.positionDropdown();
            }
        }, true);
    }
    
    positionDropdown() {
        const rect = this.trigger.getBoundingClientRect();
        this.dropdown.style.top = `${rect.bottom + 4}px`;
        this.dropdown.style.left = `${rect.left}px`;
        this.dropdown.style.width = `${rect.width}px`;
    }
    
    toggleDropdown() {
        if (this.wrapper.classList.contains('open')) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }
    
    openDropdown() {
        // Close other dropdowns
        document.querySelectorAll('.custom-select-wrapper.open').forEach(wrapper => {
            wrapper.classList.remove('open');
        });
        document.querySelectorAll('.custom-select-dropdown.show').forEach(dd => {
            dd.classList.remove('show');
            if (dd.parentNode === document.body) {
                document.body.removeChild(dd);
            }
        });
        
        this.wrapper.classList.add('open');
        this.positionDropdown();
        document.body.appendChild(this.dropdown);
        
        // Add show class after a small delay for transition
        setTimeout(() => {
            this.dropdown.classList.add('show');
        }, 10);
    }
    
    closeDropdown() {
        this.wrapper.classList.remove('open');
        this.dropdown.classList.remove('show');
        
        // Remove from DOM after transition
        setTimeout(() => {
            if (this.dropdown.parentNode === document.body) {
                document.body.removeChild(this.dropdown);
            }
        }, 300);
    }
    
    selectOption(optionElement) {
        const index = parseInt(optionElement.dataset.index);
        const value = optionElement.dataset.value;
        
        // Update UI
        this.dropdown.querySelectorAll('.custom-select-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        optionElement.classList.add('selected');
        
        this.trigger.querySelector('.custom-select-value').textContent = optionElement.textContent;
        
        // Update original select
        this.select.selectedIndex = index;
        this.select.value = value;
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        this.select.dispatchEvent(event);
        
        this.closeDropdown();
    }
}

// Initialize custom selects on page load
document.addEventListener('DOMContentLoaded', () => {
    // Apply to all devices
    document.querySelectorAll('select.form-control-glass, select.form-select').forEach(select => {
        new CustomSelect(select);
    });
});
