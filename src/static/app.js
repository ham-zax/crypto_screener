/**
 * Project Omega - Crypto Screening Application
 * Implements the Omega Protocol with localStorage persistence
 */

class OmegaApp {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 3;
        this.projects = [];
        this.filteredProjects = [];
        
        this.init();
    }

    init() {
        this.loadProjects();
        this.setupEventListeners();
        this.updateProgressIndicator();
        this.renderProjectList();
        this.updateProjectCount();
    }

    // ===== LOCALSTORAGE OPERATIONS =====
    
    loadProjects() {
        try {
            const stored = localStorage.getItem('omega_projects');
            this.projects = stored ? JSON.parse(stored) : [];
            this.filteredProjects = [...this.projects];
        } catch (error) {
            console.error('Error loading projects from localStorage:', error);
            this.projects = [];
            this.filteredProjects = [];
        }
    }

    saveProjects() {
        try {
            localStorage.setItem('omega_projects', JSON.stringify(this.projects));
        } catch (error) {
            console.error('Error saving projects to localStorage:', error);
            this.showError('Failed to save project data. Please check if localStorage is available.');
        }
    }

    // ===== OMEGA SCORE CALCULATIONS =====

    calculateOmegaScore(project) {
        // Narrative Score: Average of 3 components
        const narrativeScore = (
            parseFloat(project.sector_strength) + 
            parseFloat(project.value_proposition) + 
            parseFloat(project.backing_team)
        ) / 3;
        
        // Tokenomics Score: Average of 3 components  
        const tokenomicsScore = (
            parseFloat(project.valuation_potential) + 
            parseFloat(project.token_utility) + 
            parseFloat(project.supply_risk)
        ) / 3;
        
        // Data Score: Single component
        const dataScore = parseFloat(project.accumulation_signal);
        
        // Final Omega Score: Weighted formula (BR-03)
        const omegaScore = (narrativeScore * 0.25) + (tokenomicsScore * 0.25) + (dataScore * 0.50);
        
        return {
            narrative_score: parseFloat(narrativeScore.toFixed(2)),
            tokenomics_score: parseFloat(tokenomicsScore.toFixed(2)), 
            data_score: dataScore,
            omega_score: parseFloat(omegaScore.toFixed(2))
        };
    }

    // ===== WIZARD LOGIC =====

    setupEventListeners() {
        const prevButton = document.getElementById('prevButton');
        const nextButton = document.getElementById('nextButton');
        const submitButton = document.getElementById('submitButton');
        const form = document.getElementById('projectWizard');

        prevButton.addEventListener('click', () => this.previousStep());
        nextButton.addEventListener('click', () => this.nextStep());
        form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Filter event listeners
        document.getElementById('filterSector').addEventListener('change', () => this.applyFilters());
        document.getElementById('filterOmegaMin').addEventListener('input', () => this.applyFilters());
        document.getElementById('filterOmegaMax').addEventListener('input', () => this.applyFilters());
        document.getElementById('clearFilters').addEventListener('click', () => this.clearFilters());

        // Form validation on input
        const inputs = form.querySelectorAll('input[required], select[required]');
        inputs.forEach(input => {
            input.addEventListener('input', () => this.validateCurrentStep());
            input.addEventListener('blur', () => this.validateCurrentStep());
        });
    }

    validateCurrentStep() {
        const currentStepElement = document.querySelector(`.wizard-step[data-step="${this.currentStep}"]`);
        const requiredFields = currentStepElement.querySelectorAll('input[required], select[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('error');
            } else {
                field.classList.remove('error');
            }
        });

        // Update next button state
        const nextButton = document.getElementById('nextButton');
        const submitButton = document.getElementById('submitButton');
        
        if (this.currentStep < this.totalSteps) {
            nextButton.disabled = !isValid;
        } else {
            submitButton.disabled = !isValid;
        }

        return isValid;
    }

    nextStep() {
        if (!this.validateCurrentStep()) {
            this.showError('All fields are required before proceeding.');
            return;
        }

        this.hideError();

        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateWizardStep();
        }
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateWizardStep();
        }
    }

    updateWizardStep() {
        // Hide all steps
        document.querySelectorAll('.wizard-step').forEach(step => {
            step.classList.remove('active');
        });

        // Show current step
        document.querySelector(`.wizard-step[data-step="${this.currentStep}"]`).classList.add('active');

        // Update step indicators
        this.updateProgressIndicator();

        // Update button states
        this.updateButtonStates();

        // Validate current step
        this.validateCurrentStep();
    }

    updateProgressIndicator() {
        const progressLine = document.getElementById('progressLine');
        const steps = document.querySelectorAll('.step');
        
        // Update progress line
        const progressPercentage = ((this.currentStep - 1) / (this.totalSteps - 1)) * 100;
        progressLine.style.width = `${progressPercentage}%`;

        // Update step states
        steps.forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNumber < this.currentStep) {
                step.classList.add('completed');
            } else if (stepNumber === this.currentStep) {
                step.classList.add('active');
            }
        });
    }

    updateButtonStates() {
        const prevButton = document.getElementById('prevButton');
        const nextButton = document.getElementById('nextButton');
        const submitButton = document.getElementById('submitButton');

        prevButton.disabled = this.currentStep === 1;

        if (this.currentStep === this.totalSteps) {
            nextButton.style.display = 'none';
            submitButton.style.display = 'inline-flex';
        } else {
            nextButton.style.display = 'inline-flex';
            submitButton.style.display = 'none';
        }
    }

    handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateCurrentStep()) {
            this.showError('All fields are required before proceeding.');
            return;
        }

        const formData = new FormData(e.target);
        const projectData = {};
        
        formData.forEach((value, key) => {
            projectData[key] = value;
        });

        // Add metadata
        projectData.id = this.generateUUID();
        projectData.created_at = new Date().toISOString();
        projectData.updated_at = new Date().toISOString();

        // Calculate scores
        const scores = this.calculateOmegaScore(projectData);
        Object.assign(projectData, scores);

        // Add to projects array
        this.projects.push(projectData);
        this.saveProjects();

        // Reset form and wizard
        this.resetWizard();
        
        // Update UI
        this.applyFilters();
        this.updateProjectCount();

        // Show success message
        this.showSuccess('Project added successfully!');
    }

    resetWizard() {
        const form = document.getElementById('projectWizard');
        form.reset();
        
        this.currentStep = 1;
        this.updateWizardStep();
        this.hideError();
        
        // Remove validation errors
        form.querySelectorAll('.error').forEach(field => {
            field.classList.remove('error');
        });
    }

    // ===== PROJECT MANAGEMENT =====

    deleteProject(projectId) {
        if (confirm('Are you sure you want to delete this project?')) {
            this.projects = this.projects.filter(p => p.id !== projectId);
            this.saveProjects();
            this.applyFilters();
            this.updateProjectCount();
            this.showSuccess('Project deleted successfully!');
        }
    }

    // ===== FILTERING =====

    applyFilters() {
        const sectorFilter = document.getElementById('filterSector').value;
        const omegaMinFilter = parseFloat(document.getElementById('filterOmegaMin').value) || 0;
        const omegaMaxFilter = parseFloat(document.getElementById('filterOmegaMax').value) || 10;

        this.filteredProjects = this.projects.filter(project => {
            // Sector filter
            if (sectorFilter && project.hot_sector !== sectorFilter) {
                return false;
            }

            // Omega score range filter (BR-02: AND conditions)
            if (project.omega_score < omegaMinFilter || project.omega_score > omegaMaxFilter) {
                return false;
            }

            return true;
        });

        this.renderProjectList();
    }

    clearFilters() {
        document.getElementById('filterSector').value = '';
        document.getElementById('filterOmegaMin').value = '';
        document.getElementById('filterOmegaMax').value = '';
        this.applyFilters();
    }

    // ===== UI RENDERING =====

    renderProjectList() {
        const projectList = document.getElementById('projectList');
        
        if (this.filteredProjects.length === 0) {
            if (this.projects.length === 0) {
                projectList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📊</div>
                        <h3>No projects yet</h3>
                        <p>Add your first cryptocurrency project using the wizard above</p>
                    </div>
                `;
            } else {
                projectList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🔍</div>
                        <h3>No projects match your filters</h3>
                        <p>Try adjusting your filter criteria</p>
                    </div>
                `;
            }
            return;
        }

        // Sort by omega score (highest first)
        const sortedProjects = [...this.filteredProjects].sort((a, b) => b.omega_score - a.omega_score);

        projectList.innerHTML = sortedProjects.map(project => `
            <div class="project-card">
                <div class="project-header">
                    <div>
                        <div class="project-name">${this.escapeHtml(project.name)}</div>
                        ${project.ticker ? `<div style="font-size: 14px; color: #666; margin-bottom: 8px;">${this.escapeHtml(project.ticker)}</div>` : ''}
                        <span class="project-sector">${this.escapeHtml(project.hot_sector)}</span>
                    </div>
                    <div class="omega-score">
                        <div class="omega-score-value ${this.getScoreClass(project.omega_score)}">${project.omega_score}</div>
                        <div class="omega-score-label">Omega Score</div>
                    </div>
                </div>
                
                <div class="score-breakdown">
                    <div class="score-item">
                        <div class="score-item-value ${this.getScoreClass(project.narrative_score)}">${project.narrative_score}</div>
                        <div class="score-item-label">Narrative</div>
                    </div>
                    <div class="score-item">
                        <div class="score-item-value ${this.getScoreClass(project.tokenomics_score)}">${project.tokenomics_score}</div>
                        <div class="score-item-label">Tokenomics</div>
                    </div>
                    <div class="score-item">
                        <div class="score-item-value ${this.getScoreClass(project.data_score)}">${project.data_score}</div>
                        <div class="score-item-label">Data</div>
                    </div>
                </div>

                <div class="project-actions">
                    <button class="btn btn-danger btn-small" onclick="app.deleteProject('${project.id}')">
                        Delete
                    </button>
                </div>
            </div>
        `).join('');
    }

    updateProjectCount() {
        const totalProjects = this.projects.length;
        const filteredCount = this.filteredProjects.length;
        const countElement = document.getElementById('projectCount');
        
        if (totalProjects === filteredCount) {
            countElement.textContent = `${totalProjects} project${totalProjects !== 1 ? 's' : ''}`;
        } else {
            countElement.textContent = `${filteredCount} of ${totalProjects} projects`;
        }
    }

    // ===== UTILITY FUNCTIONS =====

    getScoreClass(score) {
        if (score >= 8.5) return 'score-excellent';
        if (score >= 7.0) return 'score-good';
        if (score >= 5.5) return 'score-average';
        return 'score-poor';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    showError(message) {
        const errorElement = document.getElementById('errorMessage');
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        errorElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    hideError() {
        const errorElement = document.getElementById('errorMessage');
        errorElement.style.display = 'none';
    }

    showSuccess(message) {
        // Create a temporary success message
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #16a34a;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        successDiv.textContent = message;
        
        // Add animation styles
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(successDiv);
        
        // Remove after 3 seconds
        setTimeout(() => {
            successDiv.remove();
            style.remove();
        }, 3000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new OmegaApp();
});