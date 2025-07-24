/**
 * Project Omega V2 - Crypto Screening Application
 * Implements the Omega Protocol with hybrid localStorage/server persistence
 * Supports both manual projects (V1) and automated projects (V2)
 */

class OmegaApp {
    constructor() {
        // V1 Properties
        this.currentStep = 1;
        this.totalSteps = 3;
        this.projects = [];
        this.filteredProjects = [];
        
        // V2 Properties
        this.currentTab = 'manual';
        this.automatedProjects = [];
        this.filteredAutomatedProjects = [];
        this.lastUpdated = null;
        this.currentCSVProjectId = null;
        this.csvChart = null; // Chart.js instance for CSV visualization
        this.selectedProjects = new Set(); // Track selected projects for bulk operations

        // Background Task Log Panel Integration
        this.logPollInterval = null;
        this.lastLogTimestamp = null;
        
        // API Base URL (adjust for your environment)
        this.apiBaseUrl = window.location.origin;
        
        this.init();
    }

    init() {
        this.loadProjects();
        this.setupEventListeners();
        this.updateProgressIndicator();
        this.renderProjectList();
        this.updateProjectCount();
        this.setupTabSwitching();
        this.loadAutomatedProjects();
        this.initializeLogPanel();
    }

    // ===== TAB SWITCHING =====
    
    setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.nav-tab');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });
    }

    switchTab(tabName) {
        console.log(`[DEBUG] switchTab called with tabName: "${tabName}"`);

        if (this.currentTab === tabName) {
            console.log('[DEBUG] Tab is already active. Doing nothing.');
            return;
        }

        this.currentTab = tabName;

        // Update tab buttons
        document.querySelectorAll('.nav-tab').forEach(btn => {
            btn.classList.remove('active');
            btn.setAttribute('aria-selected', 'false');
        });
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
            activeTab.setAttribute('aria-selected', 'true');
            console.log('[DEBUG] Active tab styles updated.');
        } else {
            console.error(`[DEBUG] Could not find tab button for tab: "${tabName}"`);
        }

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const activeContent = document.getElementById(`${tabName}Tab`);
        if (activeContent) {
            activeContent.classList.add('active');
            console.log('[DEBUG] Active content panel updated.');
        } else {
            console.error(`[DEBUG] Could not find content panel for tab: "${tabName}"`);
        }
        
        // Load data for the active tab
        if (tabName === 'automated') {
            console.log('[DEBUG] "automated" tab selected. Calling loadAutomatedProjects...');
            this.loadAutomatedProjects();
        } else {
            console.log(`[DEBUG] "${tabName}" tab selected. No data load needed.`);
        }
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

        // Manual project filters
        document.getElementById('filterSector').addEventListener('change', () => this.applyFilters());
        document.getElementById('filterOmegaMin').addEventListener('input', () => this.applyFilters());
        document.getElementById('filterOmegaMax').addEventListener('input', () => this.applyFilters());
        document.getElementById('clearFilters').addEventListener('click', () => this.clearFilters());

        // Automated project filters and search
        document.getElementById('automatedSearchInput').addEventListener('input', () => this.applyAutomatedFilters());
        document.getElementById('automatedFilterSector').addEventListener('change', () => this.applyAutomatedFilters());
        document.getElementById('automatedFilterMarketCap').addEventListener('change', () => this.applyAutomatedFilters());
        document.getElementById('automatedFilterDataStatus').addEventListener('change', () => this.applyAutomatedFilters());
        document.getElementById('automatedFilterOmegaMin').addEventListener('input', () => this.applyAutomatedFilters());
        document.getElementById('automatedSortBy').addEventListener('change', () => this.applyAutomatedFilters());
        document.getElementById('clearAutomatedFilters').addEventListener('click', () => this.clearAutomatedFilters());

        // Automated project controls
        document.getElementById('refreshAutomatedProjects').addEventListener('click', () => this.refreshAutomatedProjects());
        
        // Bulk operation controls
        document.getElementById('selectAllBtn').addEventListener('click', () => this.selectAllProjects());
        document.getElementById('clearSelectionBtn').addEventListener('click', () => this.clearSelection());
        document.getElementById('bulkAnalyzeBtn').addEventListener('click', () => this.bulkAnalyzeProjects());

        // Form validation on input
        const inputs = form.querySelectorAll('input[required], select[required]');
        inputs.forEach(input => {
            input.addEventListener('input', () => this.validateCurrentStep());
            input.addEventListener('blur', () => this.validateCurrentStep());
        });
    }

    // ===== V2 API CLIENT FUNCTIONS =====

    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const config = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            if (data) {
                config.body = JSON.stringify(data);
            }

            const response = await fetch(`${this.apiBaseUrl}${endpoint}`, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API call failed for ${endpoint}:`, error);
            throw error;
        }
    }

    async loadAutomatedProjects() {
        console.log('[DEBUG] loadAutomatedProjects function started.');
        try {
            console.log('[DEBUG] About to make API call to /api/v2/projects/automated');
            const response = await this.apiCall('/api/v2/projects/automated');
            console.log('[DEBUG] API call successful. Response received:', response);

            this.automatedProjects = response.data || [];
            this.lastUpdated = response.last_updated ? new Date(response.last_updated) : new Date();
            
            console.log(`[DEBUG] Loaded ${this.automatedProjects.length} automated projects.`);
            
            this.applyAutomatedFilters();
            this.updateLastUpdatedDisplay();
        } catch (error) {
            console.error('[DEBUG] Failed to load automated projects:', error);
            this.showAutomatedProjectsError('Failed to load automated projects. Check console for details.');
        }
    }

    async refreshAutomatedProjects() {
        const refreshButton = document.getElementById('refreshAutomatedProjects');
        const spinner = document.getElementById('refreshSpinner');
        
        refreshButton.disabled = true;
        spinner.style.display = 'inline-block';

        try {
            const result = await this.apiCall('/api/v2/tasks/fetch-projects', 'POST', {
                save_to_database: true,
                priority: 5
            });

            if (result.task_id) {
                this.showSuccess('Project fetch started in the background. The list will update automatically when complete.');
                // Poll for completion and then refresh
                this.pollTaskStatus(result.task_id);
            } else {
                this.showError('Failed to start background refresh task.');
                refreshButton.disabled = false;
                spinner.style.display = 'none';
            }
            
        } catch (error) {
            console.error('Failed to trigger refresh task:', error);
            this.showError('Failed to trigger refresh task. Please try again.');
            refreshButton.disabled = false;
            spinner.style.display = 'none';
        }
    }

    // === Task Status Display Integration ===
    async pollTaskStatus(taskId) {
        const taskStatusElement = document.getElementById('taskStatusDisplay');
        const refreshButton = document.getElementById('refreshAutomatedProjects');
        const spinner = document.getElementById('refreshSpinner');
        const logOutput = document.getElementById('logOutput');
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/v2/tasks/status?task_id=${taskId}`);
                const statusResult = await response.json();
                const task = statusResult.task_status;
                if (task && (task.status === 'SUCCESS' || task.status === 'COMPLETED')) {
                    if (taskStatusElement) {
                        taskStatusElement.textContent = `Task ${taskId} completed successfully.`;
                    }
                    if (logOutput) {
                        const successMsg = `[${new Date().toISOString()}] INFO: Task ${taskId} completed successfully.\n`;
                        logOutput.textContent += successMsg;
                        logOutput.scrollTop = logOutput.scrollHeight;
                    }
                    refreshButton.disabled = false;
                    spinner.style.display = 'none';
                    clearInterval(interval);
                    // FIX #1: Refresh the project list on successful completion.
                    await this.loadAutomatedProjects();
                } else if (task && task.status === 'FAILURE') {
                    if (taskStatusElement) {
                        taskStatusElement.textContent = `Task ${taskId} failed. Reason: ${task.result || 'Unknown'}`;
                    }
                    if (logOutput) {
                        const errorMsg = `[${new Date().toISOString()}] ERROR: Task ${taskId} failed. Reason: ${task.result || 'Unknown'}\n`;
                        logOutput.textContent += errorMsg;
                        logOutput.scrollTop = logOutput.scrollHeight;
                    }
                    refreshButton.disabled = false;
                    spinner.style.display = 'none';
                    clearInterval(interval);
                } else if (task && task.status === 'PROGRESS') {
                    const progressMsg = `Progress: ${task.meta?.current || 0}/${task.meta?.total || '??'} - ${task.meta?.status || 'Processing...'}`;
                    if (taskStatusElement) {
                        taskStatusElement.textContent = progressMsg;
                    }
                }
            } catch (error) {
                if (taskStatusElement) {
                    taskStatusElement.textContent = `Error polling task status: ${error.message}`;
                }
                refreshButton.disabled = false;
                spinner.style.display = 'none';
                clearInterval(interval);
            }
        }, 5000);
    }

    async analyzeCSVData(projectId, csvText) {
        try {
            const result = await this.apiCall(`/api/v2/projects/automated/${projectId}/csv`, 'POST', {
                csv_data: csvText
            });
            return result;
        } catch (error) {
            console.error('CSV analysis failed:', error);
            throw error;
        }
    }

    // ===== AUTOMATED PROJECT FILTERING =====

    applyAutomatedFilters() {
        const searchInput = document.getElementById('automatedSearchInput').value.toLowerCase().trim();
        const sectorFilter = document.getElementById('automatedFilterSector').value;
        const marketCapFilter = parseFloat(document.getElementById('automatedFilterMarketCap').value) || 0;
        const dataStatusFilter = document.getElementById('automatedFilterDataStatus').value;
        const omegaMinFilter = parseFloat(document.getElementById('automatedFilterOmegaMin').value) || 0;
        const sortBy = document.getElementById('automatedSortBy').value;

        this.filteredAutomatedProjects = this.automatedProjects.filter(project => {
            // Search filter
            if (searchInput) {
                const searchableText = `${project.name} ${project.ticker || ''}`.toLowerCase();
                if (!searchableText.includes(searchInput)) {
                    return false;
                }
            }

            // Sector filter
            if (sectorFilter && project.category !== sectorFilter) {
                return false;
            }

            // Market cap filter
            if (marketCapFilter > 0 && project.market_cap < marketCapFilter) {
                return false;
            }

            // Data status filter
            if (dataStatusFilter === 'awaiting' && project.has_data_score) {
                return false;
            }
            if (dataStatusFilter === 'complete' && !project.has_data_score) {
                return false;
            }

            // Omega score filter (only for projects with complete scores)
            if (project.has_data_score && project.omega_score < omegaMinFilter) {
                return false;
            }

            return true;
        });

        // Apply sorting
        this.sortAutomatedProjects(sortBy);
        this.renderAutomatedProjectList();
    }

    sortAutomatedProjects(sortBy) {
        this.filteredAutomatedProjects.sort((a, b) => {
            switch (sortBy) {
                case 'omega_desc':
                    if (a.has_data_score && b.has_data_score) {
                        return b.omega_score - a.omega_score;
                    } else if (a.has_data_score !== b.has_data_score) {
                        return a.has_data_score ? 1 : -1; // Awaiting data first
                    } else {
                        const aScore = (a.narrative_score + a.tokenomics_score) / 2;
                        const bScore = (b.narrative_score + b.tokenomics_score) / 2;
                        return bScore - aScore;
                    }
                case 'omega_asc':
                    if (a.has_data_score && b.has_data_score) {
                        return a.omega_score - b.omega_score;
                    } else if (a.has_data_score !== b.has_data_score) {
                        return b.has_data_score ? 1 : -1; // Complete data first
                    } else {
                        const aScore = (a.narrative_score + a.tokenomics_score) / 2;
                        const bScore = (b.narrative_score + b.tokenomics_score) / 2;
                        return aScore - bScore;
                    }
                case 'market_cap_desc':
                    return (b.market_cap || 0) - (a.market_cap || 0);
                case 'market_cap_asc':
                    return (a.market_cap || 0) - (b.market_cap || 0);
                case 'name_asc':
                    return a.name.localeCompare(b.name);
                case 'data_status':
                    if (a.has_data_score === b.has_data_score) {
                        return b.omega_score - a.omega_score; // Secondary sort by omega score
                    }
                    return a.has_data_score ? 1 : -1; // Awaiting data first
                default:
                    return 0;
            }
        });
    }

    clearAutomatedFilters() {
        document.getElementById('automatedSearchInput').value = '';
        document.getElementById('automatedFilterSector').value = '';
        document.getElementById('automatedFilterMarketCap').value = '';
        document.getElementById('automatedFilterDataStatus').value = '';
        document.getElementById('automatedFilterOmegaMin').value = '';
        document.getElementById('automatedSortBy').value = 'omega_desc';
        this.clearSelection();
        this.applyAutomatedFilters();
    }

    // ===== AUTOMATED PROJECT RENDERING =====

    renderAutomatedProjectList() {
        const projectList = document.getElementById('automatedProjectList');
        
        if (this.filteredAutomatedProjects.length === 0) {
            if (this.automatedProjects.length === 0) {
                projectList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🤖</div>
                        <h3>Loading automated projects...</h3>
                        <p>Fetching cryptocurrency data from market APIs</p>
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

        projectList.innerHTML = this.filteredAutomatedProjects.map(project => this.renderAutomatedProjectCard(project)).join('');
        this.updateSelectionControls();
    }

    renderAutomatedProjectCard(project) {
        const isAwaitingData = !project.has_data_score;
        const isSelected = this.selectedProjects.has(project.id);
        const omegaScoreDisplay = isAwaitingData ?
            { value: 'N/A', label: 'Awaiting Data', class: 'awaiting' } :
            { value: project.omega_score, label: 'Omega Score', class: this.getScoreClass(project.omega_score) };

        const marketCapFormatted = this.formatMarketCap(project.market_cap);
        
        return `
            <div class="project-card ${isSelected ? 'selected' : ''}" data-project-id="${project.id}">
                <div class="project-header">
                    <div style="display: flex; align-items: flex-start; gap: 12px;">
                        <input type="checkbox"
                               class="project-checkbox"
                               data-project-id="${project.id}"
                               ${isSelected ? 'checked' : ''}
                               onchange="toggleProjectSelection('${project.id}')"
                               style="margin-top: 4px;">
                        <div style="flex: 1;">
                            <div class="project-name">${this.escapeHtml(project.name)}</div>
                            ${project.ticker ? `<div style="font-size: 14px; color: #666; margin-bottom: 8px;">${this.escapeHtml(project.ticker)}</div>` : ''}
                            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px;">
                                <span class="project-sector">${this.escapeHtml(project.category || 'Other')}</span>
                                <span class="project-source-indicator source-automated">Auto</span>
                            </div>
                            <div style="font-size: 12px; color: #666;">
                                Market Cap: ${marketCapFormatted}
                            </div>
                        </div>
                    </div>
                    <div class="omega-score ${omegaScoreDisplay.class}">
                        <div class="omega-score-value">${omegaScoreDisplay.value}</div>
                        <div class="omega-score-label">${omegaScoreDisplay.label}</div>
                    </div>
                </div>
                
                <div class="score-breakdown">
                    <div class="score-item">
                        <div class="score-item-value ${this.getScoreClass(project.narrative_score)}">${project.narrative_score}</div>
                        <div class="score-item-label">Narrative</div>
                        <div style="font-size: 10px; color: #666;">Auto</div>
                    </div>
                    <div class="score-item">
                        <div class="score-item-value ${this.getScoreClass(project.tokenomics_score)}">${project.tokenomics_score}</div>
                        <div class="score-item-label">Tokenomics</div>
                        <div style="font-size: 10px; color: #666;">Auto</div>
                    </div>
                    <div class="score-item ${isAwaitingData ? 'awaiting-data' : ''}">
                        <div class="score-item-value ${isAwaitingData ? 'awaiting-data' : this.getScoreClass(project.data_score)}">
                            ${isAwaitingData ? '--' : project.data_score}
                        </div>
                        <div class="score-item-label">Data</div>
                        <div style="font-size: 10px; color: #666;">Manual</div>
                    </div>
                </div>

                <div class="project-actions">
                    ${isAwaitingData ?
                        `<button class="btn btn-primary btn-small" onclick="openCSVModal('${project.id}', '${this.escapeHtml(project.name)}')">
                            📊 Add Data
                        </button>` :
                        `<button class="btn btn-secondary btn-small" onclick="openCSVModal('${project.id}', '${this.escapeHtml(project.name)}')">
                            📊 Update Data
                        </button>`
                    }
                    <button class="btn btn-secondary btn-small" onclick="viewAutomatedProjectDetails('${project.id}')">
                        Details
                    </button>
                </div>
            </div>
        `;
    }

    showAutomatedProjectsError(message) {
        const projectList = document.getElementById('automatedProjectList');
        projectList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <h3>Error Loading Projects</h3>
                <p>${message}</p>
                <button class="btn btn-primary" onclick="app.loadAutomatedProjects()">Retry</button>
            </div>
        `;
    }

    updateLastUpdatedDisplay() {
        const lastUpdatedElement = document.getElementById('lastUpdated');
        if (this.lastUpdated) {
            const timeAgo = this.getTimeAgo(this.lastUpdated);
            lastUpdatedElement.textContent = `Last updated: ${timeAgo}`;
        }
    }

    formatMarketCap(marketCap) {
        if (!marketCap) return 'N/A';
        
        if (marketCap >= 1_000_000_000) {
            return `$${(marketCap / 1_000_000_000).toFixed(1)}B`;
        } else if (marketCap >= 1_000_000) {
            return `$${(marketCap / 1_000_000).toFixed(1)}M`;
        } else if (marketCap >= 1_000) {
            return `$${(marketCap / 1_000).toFixed(1)}K`;
        } else {
            return `$${marketCap.toFixed(0)}`;
        }
    }

    getTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return `${diffInSeconds} seconds ago`;
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        return `${Math.floor(diffInSeconds / 86400)} days ago`;
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

    // ===== CSV UPLOAD MODAL FUNCTIONS =====

    setupCSVModal() {
        const csvInput = document.getElementById('csvInput');
        
        // Drag and drop functionality
        csvInput.addEventListener('dragover', (e) => {
            e.preventDefault();
            csvInput.classList.add('drag-over');
        });

        csvInput.addEventListener('dragleave', (e) => {
            e.preventDefault();
            csvInput.classList.remove('drag-over');
        });

        csvInput.addEventListener('drop', (e) => {
            e.preventDefault();
            csvInput.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        csvInput.value = event.target.result;
                    };
                    reader.readAsText(file);
                } else {
                    this.showError('Please drop a CSV file.');
                }
            }
        });
    }

    async handleCSVAnalysis(projectId, csvText) {
        const analyzeButton = document.getElementById('analyzeCSVButton');
        const spinner = document.getElementById('analyzeSpinner');
        
        analyzeButton.disabled = true;
        spinner.style.display = 'inline-block';

        try {
            const result = await this.analyzeCSVData(projectId, csvText);
            
            // Display results
            this.displayCSVAnalysisResults(result);
            
            // Refresh automated projects to show updated score
            await this.loadAutomatedProjects();
            
            this.showSuccess('Data analysis completed successfully!');
        } catch (error) {
            console.error('CSV analysis failed:', error);
            this.showError('Failed to analyze CSV data. Please check the format and try again.');
        } finally {
            analyzeButton.disabled = false;
            spinner.style.display = 'none';
        }
    }

    displayCSVAnalysisResults(result) {
        const resultsDiv = document.getElementById('analysisResults');
        const dataScore = document.getElementById('dataScore');
        const priceTrend = document.getElementById('priceTrend');
        const cvdTrend = document.getElementById('cvdTrend');
        const divergenceAnalysis = document.getElementById('divergenceAnalysis');
        const dataPoints = document.getElementById('dataPoints');

        dataScore.textContent = result.data_score;
        dataScore.className = `score ${this.getScoreClass(result.data_score)}`;
        
        priceTrend.textContent = result.analysis.price_trend > 0 ? '📈 Upward' : '📉 Downward';
        cvdTrend.textContent = result.analysis.cvd_trend > 0 ? '📈 Accumulation' : '📉 Distribution';
        divergenceAnalysis.textContent = result.analysis.divergence_type || 'None';
        dataPoints.textContent = result.analysis.data_points || '--';

        resultsDiv.style.display = 'block';
        
        // Create chart visualization if data is available
        if (result.chart_data && result.chart_data.length > 0) {
            this.createCSVChart(result.chart_data);
        }
    }

    createCSVChart(chartData) {
        const chartContainer = document.getElementById('chartContainer');
        const canvas = document.getElementById('csvChart');
        
        // Destroy existing chart if it exists
        if (this.csvChart) {
            this.csvChart.destroy();
        }
        
        // Show chart container
        chartContainer.style.display = 'block';
        
        // Prepare data for Chart.js
        const labels = chartData.map(point => point.time);
        const priceData = chartData.map(point => point.close);
        const cvdData = chartData.map(point => point.cvd);
        
        // Normalize CVD data to price scale for better visualization
        const priceMin = Math.min(...priceData);
        const priceMax = Math.max(...priceData);
        const cvdMin = Math.min(...cvdData);
        const cvdMax = Math.max(...cvdData);
        
        const normalizedCVD = cvdData.map(cvd => {
            return priceMin + ((cvd - cvdMin) / (cvdMax - cvdMin)) * (priceMax - priceMin);
        });
        
        const ctx = canvas.getContext('2d');
        this.csvChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Price',
                        data: priceData,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'CVD (Normalized)',
                        data: normalizedCVD,
                        borderColor: '#16a34a',
                        backgroundColor: 'rgba(22, 163, 74, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        ticks: {
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Price'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            afterLabel: function(context) {
                                if (context.datasetIndex === 1) {
                                    // Show original CVD value in tooltip
                                    const originalCVD = cvdData[context.dataIndex];
                                    return `Original CVD: ${originalCVD.toLocaleString()}`;
                                }
                                return '';
                            }
                        }
                    }
                }
            }
        });
    }

    // ===== BULK OPERATIONS AND SELECTION =====

    selectAllProjects() {
        const awaitingDataProjects = this.filteredAutomatedProjects.filter(p => !p.has_data_score);
        awaitingDataProjects.forEach(project => {
            this.selectedProjects.add(project.id);
        });
        this.renderAutomatedProjectList();
    }

    clearSelection() {
        this.selectedProjects.clear();
        this.renderAutomatedProjectList();
    }

    toggleProjectSelection(projectId) {
        if (this.selectedProjects.has(projectId)) {
            this.selectedProjects.delete(projectId);
        } else {
            this.selectedProjects.add(projectId);
        }
        this.updateSelectionControls();
    }

    updateSelectionControls() {
        const selectionCount = document.getElementById('selectionCount');
        const bulkAnalyzeBtn = document.getElementById('bulkAnalyzeBtn');
        const selectAllBtn = document.getElementById('selectAllBtn');
        const clearSelectionBtn = document.getElementById('clearSelectionBtn');

        const selectedCount = this.selectedProjects.size;
        const awaitingDataCount = this.filteredAutomatedProjects.filter(p => !p.has_data_score).length;

        selectionCount.textContent = `${selectedCount} selected`;

        if (selectedCount > 0) {
            bulkAnalyzeBtn.style.display = 'inline-block';
            clearSelectionBtn.style.display = 'inline-block';
        } else {
            bulkAnalyzeBtn.style.display = 'none';
            clearSelectionBtn.style.display = 'none';
        }

        // Update select all button text
        if (selectedCount === awaitingDataCount && awaitingDataCount > 0) {
            selectAllBtn.textContent = 'Select All';
            selectAllBtn.disabled = true;
        } else {
            selectAllBtn.textContent = `Select All (${awaitingDataCount})`;
            selectAllBtn.disabled = awaitingDataCount === 0;
        }
    }

    async bulkAnalyzeProjects() {
        const selectedProjectIds = Array.from(this.selectedProjects);
        if (selectedProjectIds.length === 0) {
            this.showError('No projects selected for bulk analysis.');
            return;
        }

        const bulkAnalyzeBtn = document.getElementById('bulkAnalyzeBtn');
        const originalText = bulkAnalyzeBtn.textContent;
        
        bulkAnalyzeBtn.disabled = true;
        bulkAnalyzeBtn.innerHTML = `<span class="loading-spinner"></span> Processing...`;

        let completed = 0;
        let failed = 0;

        for (const projectId of selectedProjectIds) {
            const project = this.automatedProjects.find(p => p.id === projectId);
            if (!project) continue;

            try {
                // In a real implementation, this would use actual CSV data
                // For now, we'll simulate with placeholder data
                const placeholderCSV = `time,close,Volume Delta (Close)
2024-01-01,45000,1500000
2024-01-02,45200,2100000
2024-01-03,44800,-800000`;
                
                await this.analyzeCSVData(projectId, placeholderCSV);
                completed++;
            } catch (error) {
                console.error(`Failed to analyze project ${project.name}:`, error);
                failed++;
            }

            // Update progress
            bulkAnalyzeBtn.textContent = `Processing... (${completed + failed}/${selectedProjectIds.length})`;
        }

        // Refresh the automated projects to show updated scores
        await this.loadAutomatedProjects();
        
        // Clear selection and reset button
        this.clearSelection();
        bulkAnalyzeBtn.disabled = false;
        bulkAnalyzeBtn.textContent = originalText;

        // Show completion message
        if (failed === 0) {
            this.showSuccess(`Successfully analyzed ${completed} projects!`);
        } else {
            this.showError(`Completed with ${completed} successful and ${failed} failed analyses.`);
        }
    }

    // === Background Task Log Panel Integration ===
    async fetchAndDisplayLogs() {
        const logOutput = document.getElementById('logOutput');
        const autoScrollCheckbox = document.getElementById('autoScrollLogsCheckbox');
        const isAutoScroll = autoScrollCheckbox && autoScrollCheckbox.checked;

        try {
            const response = await fetch('/api/v2/logs/background-tasks?since=' + (this.lastLogTimestamp ? encodeURIComponent(this.lastLogTimestamp) : ''));
            if (!response.ok) {
                if (response.status === 404) return;
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const logsData = await response.json();
            const logs = logsData.logs || [];

            if (logs.length > 0) {
                let shouldScroll = false;
                if (isAutoScroll) {
                    const isScrolledToBottom = logOutput.scrollHeight - logOutput.clientHeight <= logOutput.scrollTop + 1;
                    shouldScroll = isScrolledToBottom;
                }

                logs.forEach(logEntry => {
                    const formattedEntry = `[${logEntry.timestamp}] ${logEntry.level}: ${logEntry.message}\n`;
                    const entryElement = document.createElement('div');
                    entryElement.className = 'log-entry';
                    entryElement.textContent = formattedEntry;
                    logOutput.appendChild(entryElement);
                    this.lastLogTimestamp = logEntry.timestamp;
                });

                if (isAutoScroll && shouldScroll) {
                    logOutput.scrollTop = logOutput.scrollHeight;
                }
            }
        } catch (error) {
            console.error("Error fetching logs:", error);
        }
    }

    initializeLogPanel() {
        const clearLogsButton = document.getElementById('clearLogsButton');
        const logOutput = document.getElementById('logOutput');
        const autoScrollCheckbox = document.getElementById('autoScrollLogsCheckbox');

        if (clearLogsButton) {
            clearLogsButton.addEventListener('click', () => {
                logOutput.textContent = '';
                this.lastLogTimestamp = null;
                this.showSuccess('Logs cleared.');
            });
        }

        this.fetchAndDisplayLogs();

        this.logPollInterval = setInterval(() => {
            this.fetchAndDisplayLogs();
        }, 5000);
    }
}
// Ensure OmegaApp is instantiated and globally accessible
window.app = new OmegaApp();