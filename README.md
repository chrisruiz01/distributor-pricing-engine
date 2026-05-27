# Distributor Price Realization & Margin Leakage Engine

Synthetic B2B distributor pricing analytics project built to mimic strategic pricing work in a complex distribution environment. 

## Live App

[Open the deployed Streamlit app](https://distributor-pricing-engine.streamlit.app/)

## MVP Scope

This project models invoice-level pricing performance across customers, SKUs, branches, reps, discounts, rebates, freight, and product cost. 

The current Streamlit app includes:

- Executive pricing KPIs with date, region, category, and customer-type filters
- Product category pocket margin analysis
- Regional exception rate analysis 
- Customer margin leakage candidates 
- Peer benchmark margin comparison
- Metric definitions for leakage analysis
- Scenario simulator for moving underpriced customers toward peer margin
- Exportable scenario recommendation list
- Price realization waterfall from list revenue to pocket margin
- Waterfall explanation for business users
- Product category pricing opportunity table
- Buyer context and willingness-to-pay signal analysis
- Service model margin visualization 

## Project Summary

A concise business-facing explanation of the pricing problem, app capabilities, pricing logic, buyer context signals, and interview positioning is available here: 

[Project Summary](docs/project-summary.md)

## Pricing Questions This Project Answers

- Where are we leaking margin?
- Which customers are priced below similar peers?
- How much margin could be recovered by moving customers toward peer benchmarks?
- How often are price exceptions being used? 
- Where do discounts, rebates, freight, and cost reduce realized margin?

## Tech Stack

- Python
- pandas / numpy
- PostgreSQL
- SQLAlchemy
- Streamlit
- Plotly

## Current Status

MVP in progress. Synthetic data generation, PostgreSQL load, and Streamlit dashboard are working. 

## Project Narrative 

This project simulates the pricing analytics environment of a complex B2B distributor. 

The app starts with executive pricing KPIs, then moves into deeper diagnostic views: 

1. **Price Realization**
    - Tracks revenue, gross margin, pocket margin, and exception activity.
    - Uses a waterfall to show how list revenue is reduced by discounts, cost, rebates, and freight. 

2. **Margin Leakage**
    - Compares customers against peer groups based on industry and customer type.
    - Estimates margin opportunity for customers performing below peer benchmarks. 

3. **Scenario Modeling**
    - Allows users to simulate capturing a portion of the gap between current margin and peer margin.
    - Produces an exportable recommendation list for follow-up action.

4. **Discount Governance** 
    - Highlights exception activity by region, product category, customer, and product segment.
    - Helps distinguish intentional discounting from potential leakage.

5. **Buyer Context / WTP Signals**
    - Compares pricing outcomes by industry, customer type, and service model. 
    - Flags cases where urgent buyer context may suggest potential under-capture. 

6. **Data Quality**
    - Validate core pricing fields before recommendations are trusted. 
    - Investigates negative margin and below-cost transactions. 

The goal is not to find a mathematically perfect price. The goal is to create a practical pricing workflow that helps Sales, Finance, and Pricing identify where to investigate, where to tighten guidance, and where margin improvement may be possible. 