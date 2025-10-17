# CLAUDE.md - VAT Application Reverse Engineering Instructions

## Mission
Analyze extracted executable code from a VAT (Value Added Tax) reporting application to understand its logical structure, functionality, and data flow. The goal is to reverse engineer the application's architecture and business logic for educational/research purposes.

## Analysis Scope
You are analyzing a software application designed to report VAT account balances to the National Revenue Authority (NRA). Focus on understanding:

1. **Application Architecture**
2. **Data Processing Logic** 
3. **Communication Protocols**
4. **Business Rules Implementation**
5. **Security Mechanisms**

## Key Analysis Areas

### 1. Application Structure
- Identify main modules and their responsibilities
- Map the application's entry points and execution flow
- Document class hierarchies and component relationships
- Analyze configuration and initialization procedures

### 2. Data Handling
- Examine data structures used for VAT calculations
- Identify input/output formats and validation logic
- Analyze database connections and data persistence
- Map data transformation pipelines

### 3. Communication Analysis
- Identify network communication protocols
- Analyze API endpoints and data exchange formats
- Document authentication and authorization mechanisms
- Examine encryption/security implementations

### 4. Business Logic
- Extract VAT calculation algorithms
- Identify reporting rules and validation logic
- Document error handling and exception management
- Analyze compliance requirements implementation

### 5. User Interface Components
- Map UI elements to underlying functionality
- Identify user input validation and processing
- Analyze reporting and export capabilities

## Analysis Methodology

### Static Analysis
1. **Code Structure Review**
   - Examine function/method signatures and call graphs
   - Identify design patterns and architectural decisions
   - Map dependencies between components

2. **String and Constant Analysis**
   - Extract hardcoded values, URLs, and configuration strings
   - Identify error messages and user-facing text
   - Look for API endpoints and database connection strings

3. **Import/Library Analysis**
   - Document external dependencies and libraries used
   - Identify cryptographic libraries and security frameworks
   - Map network and database connectivity libraries

### Dynamic Analysis Preparation
1. **Control Flow Mapping**
   - Trace execution paths through the application
   - Identify decision points and conditional logic
   - Map user interaction flows

2. **Data Flow Analysis**
   - Track how VAT data moves through the system
   - Identify transformation and calculation points
   - Map input validation and output formatting

## Deliverable Structure

### 1. Executive Summary
- High-level architecture overview
- Key findings and notable implementation details
- Security considerations identified

### 2. Technical Analysis
#### Architecture Documentation
- Component diagram with responsibilities
- Data flow diagrams
- Sequence diagrams for key operations

#### Functionality Breakdown
- VAT calculation logic documentation
- Reporting workflow analysis
- Data validation rules

#### Security Assessment
- Authentication/authorization mechanisms
- Data encryption methods
- Communication security analysis

### 3. Code Analysis Report
#### Module Analysis
For each significant module/component:
- Purpose and functionality
- Key methods/functions
- Data structures used
- External dependencies

#### Business Logic Documentation
- VAT calculation algorithms
- Reporting rules and formats
- Compliance checks and validations

### 4. Recommendations
- Architectural insights
- Potential improvements or modernization opportunities
- Security considerations

## Analysis Guidelines

### Focus Areas
- **Prioritize** business logic and VAT-specific functionality
- **Document** all external communications and data formats
- **Map** user workflows and system interactions
- **Identify** configuration options and customizations

### Documentation Standards
- Use clear, technical language
- Include code snippets where relevant (without reproducing large blocks)
- Create visual diagrams for complex relationships
- Provide context for technical decisions

### Ethical Considerations
- Focus on understanding functionality, not bypassing security
- Document findings for educational/research purposes
- Respect intellectual property considerations
- Maintain professional analysis standards

## Output Format
Structure your analysis in markdown format with:
- Clear section headers
- Code snippets (brief examples only)
- Diagram descriptions
- Bullet-pointed findings
- Technical specifications in tables where appropriate

## Tools and Techniques
When analyzing the extracted code:
- Use static analysis techniques to understand structure
- Focus on API calls and external integrations
- Identify configuration files and parameters
- Map database schemas and data models
- Trace user input validation and processing

Remember: The goal is to understand how the application works, its architecture, and business logic implementation - not to create exploits or bypass security measures.