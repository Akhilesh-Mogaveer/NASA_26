
import pandas as pd
import networkx as nx

# Load our two cleaned datasets
companies = pd.read_csv("data/processed/clean_companies.csv")
relations = pd.read_csv("data/processed/clean_relations.csv")

# Create an empty directed graph
# DiGraph means Directed Graph: connections have arrows
G = nx.DiGraph()

# Add all companies as nodes
# iterrows() reads the company table one row at a time
for index, company in companies.iterrows():

    # add_node() adds one company to our graph
    # The extra information is stored as attributes of that node
    G.add_node(
        company["id"],
        name=company["name"],
        country=company["country"],
        sector=company["sector"],
        segment=company["segment"]
    )

# Add supplier-customer relationships as directed edges
for index, relation in relations.iterrows():

    # add_edge() connects two nodes with an arrow
    # The arrow starts at the supplier and points to the customer
    G.add_edge(
        relation["supplier_id"],
        relation["customer_id"]
    )

# Display the total number of companies (nodes)
print("\nTOTAL COMPANIES (NODES)")
print(G.number_of_nodes())

# Display the total number of supply relationships (edges)
print("\nTOTAL RELATIONSHIPS (EDGES)")
print(G.number_of_edges())

# Display the first 10 companies in the graph
print("\nFIRST 10 COMPANIES")
print(list(G.nodes())[:10])

# Display the first 10 supply relationships
print("\nFIRST 10 RELATIONSHIPS")
print(list(G.edges())[:10])

# Display a company's details stored in the graph
print("\nDETAILS OF AGILENT")
print(G.nodes["a"])
