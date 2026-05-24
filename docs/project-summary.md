# Distributor Price Realization & Margin Leakage Engine 

## Project Objective 

This project simulates a B2B distributor pricing analytics workflow focused on identifying margin leakage, discount exceptions, and price realization opportunities. 

The goal is to help pricing, sales, and finance teams answer: 

- Where are we losing margin?
- Which customers or product categories are underpriced relative to peers?
- Where are discount exceptions concentrated? 
- What is the financial upside of moving selected customers toward benchmark margin?
- Which buyer contexts may signal higher or lower willingness to pay?

## Business Context

B2B distributors often sell thousands of SKUs across customer types, regions, product categories, and service models. Even when list prices are set correctly, margin can leak through inconsistent discounts, override behavior, freight terms, service costs, below-cost transactions, and poor price execution. 

This project focuses on price realization: whether the business is actually capturing the prices and margins it intended to capture. 

## Key Capabilities

The Streamlit app includes:

- Executive pricing KPIs
- Date, region, category, and customer-type filters
- Product category pocket margin analysis
- Regional discount exception analysis
- Customer margin leakage candidates
- Peer benchmark margin comparison
- Scenario simulator for pricing upside
- Exportable scenario recommendations
- Price realization waterfall from list revenue to pocket margin
- Product category pricing opportunity table
- Buyer context and willingness-to-pay signals
- Service model margin visualization
- Data quality checks
- Waterfall reconciliation
- Below-cost transaction investigation
- Exception heatmap by region and product category

## Pricing Logic

The project uses distributor-style pricing concepts including:

- List revenue
- Invoice revenue
- Pocket revenue
- Cost of goods sold
- Freight cost
- Service cost 
- Rebates
- Pocket margin 
- Discount exceptions
- Peer margin benchmarks
- Margin gap to peer 
- Scenario-based margin recovery

## Buyer Context / WTP Signals

The app includes buyer context signals that may affect willingness to pay, such as: 

- Emergency orders
- Special orders
- Expedited freight
- Rep-assisted orders
- Contracted vs. non-contracted buyers
- Discount exception behavior

These signals are not treated as perfect proof of willingness to pay. They are used as pricing investigation cues.

## Scenario Modeling

The scenario simulator estimates the upside from moving underpriced customers partially toward peer benchmark margin.

This allows the user to test different assumptions rather than assuming that every customer can be moved fully to target margin.

## Data Quality

The app includes data quality checks because pricing decisions are only as credible as the transaction data behind them. 

Current checks include:

- Missing values 
- Negative or below-cost margin outcomes 
- Waterfall reconciliation
- Transaction count validation
- Below-cost transaction investigation

## Interview Positioning

This project was built to mimic the type of work a strategic pricing analyst might do at a B2B distributor. 

It demonstrates the ability to:

- Analyze margin leakage
- Investigate discount exception patterns 
- Use SQL and Python for pricing analytics
- Build executive-facing dashboards
- Translate transaction data into pricing recommendations
- Connect pricing actions to buyer context and willingness to pay
- Communicate financial upside through scenario modeling