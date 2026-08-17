# Inventory Reconciliation & Dashboard

# Inventory Reconciliation System

## Overview

The Inventory Reconciliation System is a Python-based project designed to compare inventory records from different sources and identify discrepancies between marketplace and warehouse data.

The project processes inventory data, identifies differences in stock levels and records reconciliation decisions in a structured log. It also generates a dashboard to make the reconciliation results easier to review.

## Project Objectives

The main objectives of the project are to:

* Compare marketplace inventory against warehouse inventory
* Identify discrepancies between the two data sources
* Highlight inventory records that require attention
* Record reconciliation decisions for traceability
* Generate a dashboard summarising reconciliation results
* Store inventory data in structured JSON format

## Project Structure

```text
inventory-reconciler/
│
├── data/
│   ├── marketplace.json
│   └── warehouse.json
│
├── logs/
│   └── decisions.jsonl
│
├── dashboard.html
├── generate_dashboard.py
└── README.md
```

### `data/marketplace.json`

Contains inventory records from the marketplace data source.

### `data/warehouse.json`

Contains inventory records from the warehouse data source.

### `generate_dashboard.py`

Python script responsible for processing the inventory data and generating the reconciliation dashboard.

### `dashboard.html`

The generated HTML dashboard used to present the reconciliation results in a more accessible format.

### `logs/decisions.jsonl`

Stores reconciliation decisions in JSON Lines format, providing a record of decisions made during the reconciliation process.

## How It Works

The reconciliation process follows these general steps:

1. Inventory data is loaded from the marketplace and warehouse JSON files.
2. Records from the two sources are compared.
3. Differences and potential discrepancies are identified.
4. Reconciliation decisions are recorded in `decisions.jsonl`.
5. The dashboard is generated using the processed results.
6. The resulting dashboard can be reviewed to understand the reconciliation outcome.

## Technologies Used

* **Python** — data processing and reconciliation logic
* **JSON** — structured inventory data storage
* **JSON Lines (JSONL)** — reconciliation decision logging
* **HTML** — dashboard presentation
* **Git** — version control
* **GitHub** — source code management and project hosting

## Data Sources

The project currently uses two primary inventory datasets:

| Data Source | Purpose                                          |
| ----------- | ------------------------------------------------ |
| Marketplace | Represents inventory recorded by the marketplace |
| Warehouse   | Represents inventory recorded by the warehouse   |

Comparing these sources allows discrepancies between reported and warehouse inventory to be identified.

## Reconciliation

The system is designed to identify situations such as:

* Matching inventory records
* Differences in stock quantities
* Inventory appearing in one source but not another
* Records requiring reconciliation or further investigation

The decision log provides a historical record of reconciliation outcomes.

## Dashboard

The project includes an HTML dashboard generated from the reconciliation process.

The dashboard is intended to provide a simple visual overview of the reconciliation results rather than requiring users to inspect the raw JSON files manually.

## Running the Project

### Requirements

You will need:

* Python 3
* Git

### Run the reconciliation

Clone the repository:

```bash
git clone <repository-url>
```

Navigate into the project directory:

```bash
cd inventory-reconciler
```

Run the dashboard generation script:

```bash
python generate_dashboard.py
```

This generates or updates the project dashboard based on the available inventory data.

### View the dashboard

Open:

```text
dashboard.html
```

in a web browser.

## Version Control

Git is used to track changes to the project.

The repository contains the source data, Python processing script, generated dashboard and reconciliation logs so that changes can be tracked over time.

## Future Improvements

Potential future improvements include:

* Adding automated tests for reconciliation logic
* Supporting larger inventory datasets
* Adding more detailed dashboard visualisations
* Adding automated data validation

* Adding a more interactive web based dashboard

## Project Status

**Current status: In development**

The core project structure includes inventory datasets, reconciliation processing, decision logging and dashboard generation. Further improvements can be made to automation, testing and visualisation.

## Author-Chloe Eluka

Developed as a software and data focused project demonstrating practical experience with Python, structured data processing, reconciliation logic, logging and dashboard generation.


