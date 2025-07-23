# Project Omega v1.0 Compliance Plan

## Executive Summary

The current implementation of the crypto screener project **does not adhere** to the Project Omega v1.0 specification. This plan outlines the comprehensive changes required to achieve full compliance with the specification requirements.

## Major Compliance Issues Identified

### 1. **CRITICAL: Data Persistence Architecture Violation (BR-05)**
- **Current State**: Uses server-side SQLite database with Flask-SQLAlchemy
- **Required State**: Must use browser `localStorage` for all data persistence
- **Impact**: Complete architectural change required

### 2. **CRITICAL: Missing Omega Score Calculation Engine (BR-03, US-03)**
- **Current State**: No scoring logic, generic text fields only
- **Required State**: Calculate weighted score from 7 specific numeric inputs
- **Formula**: `(Narrative Score * 0.25) + (Tokenomics Score * 0.25) + (Data Score * 0.50)`

### 3. **CRITICAL: Incorrect User Interface (BR-04)**
- **Current State**: Single long HTML form
- **Required State**: Three-step wizard (Narrative → Tokenomics → Data)

### 4. **CRITICAL: Missing Filter Functionality (US-02)**
- **Current State**: No filtering capabilities
- **Required State**: Filter by Hot Sector, Omega Score range, and other criteria

### 5. **SCOPE VIOLATION: Out-of-Scope Features Implemented**
- **Current State**: Full user account system implemented
- **Required State**: No server-side accounts (Section 2.2 exclusion)

## Detailed Implementation Plan

### Phase 1: Architecture Transformation
#### 1.1 Remove Server-Side Infrastructure
- [ ] Delete [`src/database.py`](src/database.py)
- [ ] Delete [`src/database/app.db`](src/database/app.db)
- [ ] Remove database imports and configuration from [`src/main.py`](src/main.py)
- [ ] Remove Flask-SQLAlchemy from [`requirements.txt`](requirements.txt)

#### 1.2 Remove User Account System
- [ ] Delete [`src/models/user.py`](src/models/user.py)
- [ ] Delete [`src/routes/user.py`](src/routes/user.py)
- [ ] Remove user-related imports from [`src/main.py`](src/main.py)

#### 1.3 Simplify Flask Application
- [ ] Convert to static file server only
- [ ] Remove all API routes
- [ ] Serve only [`static/index.html`](src/static/index.html) and assets

### Phase 2: Data Model Redesign
#### 2.1 Define Omega Score Data Structure
```javascript
// localStorage structure for projects
{
  "omega_projects": [
    {
      "id": "uuid",
      "name": "Project Name",
      "ticker": "SYMBOL",
      "hot_sector": "AI|DePIN|RWA|GameFi|etc",
      
      // Narrative Pillar (Step 1)
      "sector_strength": 8,      // 1-10 rating
      "value_proposition": 7,    // 1-10 rating  
      "backing_team": 9,         // 1-10 rating
      
      // Tokenomics Pillar (Step 2)
      "valuation_potential": 6,  // 1-10 rating
      "token_utility": 8,        // 1-10 rating
      "supply_risk": 7,          // 1-10 rating
      
      // Data Pillar (Step 3)
      "accumulation_signal": 9,  // 1-10 rating
      
      // Calculated scores
      "narrative_score": 8.0,    // Average of narrative ratings
      "tokenomics_score": 7.0,   // Average of tokenomics ratings
      "data_score": 9.0,         // Data pillar score
      "omega_score": 8.25,       // Final weighted score
      
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Phase 3: Three-Step Wizard Implementation
#### 3.1 Wizard Step Structure
- **Step 1 - Narrative Pillar**: Sector Strength, Value Proposition, Backing & Team
- **Step 2 - Tokenomics Pillar**: Valuation Potential, Token Utility, Supply Risk  
- **Step 3 - Data Pillar**: Accumulation Signal

#### 3.2 Wizard Navigation Requirements
- [ ] "Next" button validation (all fields required)
- [ ] "Back" button with data preservation
- [ ] Progress indicator showing current step
- [ ] Form abandonment handling (data discarded)

#### 3.3 Input Validation
- [ ] All scoring fields: 1-10 numeric range
- [ ] Required field validation before step progression
- [ ] Error message display: "All fields are required before proceeding"

### Phase 4: Omega Score Calculation Engine
#### 4.1 Score Calculation Logic
```javascript
function calculateOmegaScore(project) {
  // Narrative Score: Average of 3 components
  const narrativeScore = (
    project.sector_strength + 
    project.value_proposition + 
    project.backing_team
  ) / 3;
  
  // Tokenomics Score: Average of 3 components  
  const tokenomicsScore = (
    project.valuation_potential + 
    project.token_utility + 
    project.supply_risk
  ) / 3;
  
  // Data Score: Single component
  const dataScore = project.accumulation_signal;
  
  // Final Omega Score: Weighted formula
  const omegaScore = (narrativeScore * 0.25) + (tokenomicsScore * 0.25) + (dataScore * 0.50);
  
  return {
    narrative_score: parseFloat(narrativeScore.toFixed(2)),
    tokenomics_score: parseFloat(tokenomicsScore.toFixed(2)), 
    data_score: dataScore,
    omega_score: parseFloat(omegaScore.toFixed(2))
  };
}
```

### Phase 5: Filter & Search Implementation
#### 5.1 Required Filter Controls
- [ ] **Hot Sector dropdown**: AI, DePIN, RWA, GameFi, etc.
- [ ] **Omega Score range**: Min/Max numeric inputs
- [ ] **Narrative Score range**: Min/Max numeric inputs
- [ ] **Tokenomics Score range**: Min/Max numeric inputs
- [ ] **Data Score range**: Min/Max numeric inputs

#### 5.2 Filter Logic (BR-02)
- [ ] Multiple filters combined with AND condition
- [ ] Real-time filtering as user types/selects
- [ ] Clear filters functionality

### Phase 6: localStorage Implementation
#### 6.1 Data Persistence Functions
```javascript
// Core localStorage operations
function saveProjects(projects) {
  localStorage.setItem('omega_projects', JSON.stringify(projects));
}

function loadProjects() {
  const data = localStorage.getItem('omega_projects');
  return data ? JSON.parse(data) : [];
}

function addProject(project) {
  const projects = loadProjects();
  project.id = generateUUID();
  project.created_at = new Date().toISOString();
  project.updated_at = new Date().toISOString();
  projects.push(project);
  saveProjects(projects);
}
```

#### 6.2 Data Validation
- [ ] Validate JSON structure on load
- [ ] Handle corrupted localStorage data gracefully
- [ ] Migrate old data format if needed

### Phase 7: UI/UX Implementation
#### 7.1 Watchlist Display
- [ ] Project cards showing Omega Score prominently
- [ ] Score breakdown (Narrative, Tokenomics, Data)
- [ ] Color-coding for score ranges (e.g., 8+ = green, 6-8 = yellow, <6 = red)
- [ ] Sort functionality (by Omega Score, name, date)

#### 7.2 Warning Messages
- [ ] Data loss warning: "Data is stored locally and will be lost if browser cache is cleared"
- [ ] Browser compatibility notice for localStorage

### Phase 8: Acceptance Criteria Validation
#### 8.1 US-01 Testing
- [ ] **Scenario 1**: Project persists after browser refresh
- [ ] **Scenario 2**: Wizard navigation preserves data
- [ ] **Scenario 3**: Incomplete data prevents progression
- [ ] **Scenario 4**: Abandoned wizard discards data

#### 8.2 US-02 Testing  
- [ ] **Scenario**: Filter for AI projects with Omega Score ≥ 8.0

#### 8.3 US-03 Testing
- [ ] **Scenario**: Verify calculation with test scores (9,7,8,10,9,7,8) = 8.17

## File Structure After Refactoring

```
crypto_screener/
├── src/
│   ├── main.py              # Simplified Flask server (static files only)
│   └── static/
│       ├── index.html       # Complete SPA with wizard + watchlist
│       ├── app.js          # localStorage logic + Omega calculations  
│       └── styles.css      # Wizard and watchlist styling
├── requirements.txt         # Minimal Flask dependencies
├── specs.md                # Original specification
└── plan.md                 # This implementation plan
```

## Risk Mitigation

### Data Loss Risk (BR-05)
- **Risk**: localStorage cleared = data lost
- **Mitigation**: Clear UI warnings, export/import functionality for backup

### Score Accuracy Risk
- **Risk**: Manual scoring introduces subjectivity
- **Mitigation**: Clear scoring guidelines in UI, consistent validation

### Browser Compatibility Risk
- **Risk**: localStorage not supported in very old browsers
- **Mitigation**: Feature detection and graceful degradation

## Success Criteria

✅ **Complete Compliance**: All BR-01 through BR-05 rules satisfied  
✅ **User Stories Delivered**: US-01, US-02, US-03 fully functional  
✅ **Acceptance Tests Pass**: All specified scenarios working  
✅ **No Out-of-Scope Features**: User accounts completely removed  
✅ **Data Persistence**: localStorage working across browser sessions  

## Implementation Timeline

- **Phase 1-2**: Infrastructure cleanup (2-3 hours)
- **Phase 3**: Wizard implementation (4-5 hours)  
- **Phase 4**: Score calculation (2-3 hours)
- **Phase 5**: Filtering system (3-4 hours)
- **Phase 6**: localStorage integration (2-3 hours)
- **Phase 7**: UI polish (2-3 hours)
- **Phase 8**: Testing & validation (2-3 hours)

**Total Estimated Effort**: 17-24 hours

---

*This plan transforms the current generic CRUD application into the specialized cryptocurrency screening tool specified in Project Omega v1.0, ensuring full compliance with all behavioral rules and user story requirements.*