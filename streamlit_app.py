import os
import yaml
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import seaborn as sns
import matplotlib.pyplot as plt

import plotly.offline as po
import plotly.graph_objects as go
from   plotly.subplots import make_subplots

from model.model import City

@st.cache_data()
def run_simulation(num_steps, parameters):
    city = City(num_steps, **parameters)
    city.run_model()

    # Get output data
    agent_out = city.datacollector.get_agent_vars_dataframe()
    model_out = city.datacollector.get_model_vars_dataframe()
    return agent_out, model_out

@st.cache_data()
def plot_output(agent_out, model_out):
    workers = np.array(model_out['workers'])
    wage = np.array(model_out['wage'])
    city_extent = np.array(model_out['city_extent'])
    time = np.arange(len(workers))

    land_out = agent_out.query("agent_type == 'Land'")

    # Prepare the data for visualization
    df = land_out.reset_index()

    # Define the color scale limits based on the minimum and maximum 'warranted_price' across all steps
    z_min = df['warranted_price'].min()
    z_max = 700. # Temp
    # z_max = df['warranted_price'].max()

    # Create a list of figures for each step
    figs = []
    for step in df['Step'].unique():
        temp_df = df[df['Step'] == step]
        hover_text = 'Warranted Price: ' + temp_df['warranted_price'].astype(str) + '<br>ID: ' + temp_df['id'].astype(str)
        fig = go.Figure(data=go.Heatmap(
            z=temp_df['warranted_price'],
            x=temp_df['x'],
            y=temp_df['y'],
            hovertext=hover_text,
            colorscale='viridis',
            zmin=z_min,
            zmax=z_max,
            colorbar=dict(title='Warranted Price 2', titleside='right')
        ))
        fig.update_layout(title=f'Step: {step}', xaxis_nticks=20, yaxis_nticks=20)
        figs.append(fig)

    # Use subplot to add a slider through each step
    final_fig = make_subplots(rows=1, cols=1)

    # Add traces from each figure to the final figure
    for i, fig in enumerate(figs, start=1):
        for trace in fig.data:
            final_fig.add_trace(
                go.Heatmap(
                    z=trace['z'],
                    x=trace['x'],
                    y=trace['y'],
                    hovertext=trace['hovertext'],
                    colorscale=trace['colorscale'],
                    zmin=z_min,
                    zmax=z_max,
                    colorbar=trace.colorbar,
                    visible=(i==1)  # only the first trace is visible
                )
            )

    # Create frames for each step
    final_fig.frames = [go.Frame(data=[figs[i].data[0]], name=str(i)) for i in range(len(figs))]

    # Create a slider to navigate through each step
    steps = [dict(label=str(i), method="animate", args=[[str(i)], dict(frame=dict(duration=300, redraw=True))]) for i in range(len(figs))]
    sliders = [dict(active=0, pad={"t": 50}, steps=steps)]

    final_fig.update_layout(height=600, width=800, title_text="Warranted Price Heatmap Over Steps", sliders=sliders)

    # Show the plot in streamlit
    st.plotly_chart(final_fig)

    # Set up the figure and axes
    fig, axes = plt.subplots(3, 2, figsize=(10, 15))
    fig.suptitle('Model Output', fontsize=16)
    
    # New plot 1L: evolution of the wage  
    axes[0, 0].plot(time, wage, color='red')
    axes[0, 0].set_title('City Extent and Wage (Rises)')
    axes[0, 0].set_title('Evolution of the wage ')
    axes[0, 0].set_xlabel('Time')
    axes[0, 0].set_ylabel('Wage')
    axes[0, 0].grid(True)

    # New plot 3L: evolution of the city extent = l?
    axes[0,1].plot(time, city_extent, color='red')
    axes[0,1].set_title('Evolution of the City Extent (Rises)')
    axes[0,1].set_xlabel('Time')
    axes[0,1].set_ylabel('City Extent')
    axes[0,1].grid(True)

    # New plot 2R:  evolution of the workforce
    axes[1, 0].plot(time, workers, color='purple') 
    axes[1, 0].set_title('Evolution of the Workforce (Rises)')
    axes[1, 0].set_xlabel('Time')
    axes[1, 0].set_ylabel('Workers')
    axes[1, 0].grid(True)

    # Plot 2L: city extent and workforce  
    axes[1, 1].plot(city_extent, workers, color='magenta')
    axes[1, 1].set_title('City Extent and Workforce (Curves Up)')
    axes[1, 1].set_xlabel('City Extent')
    axes[1, 1].set_ylabel('Workers')
    axes[1, 1].grid(True)              
    
    # New plot 3L: city extent and wage
    axes[2, 0].plot(time, city_extent, color='red')
    # axes[2, 0].set_title('City Extent and Wage (Linear)')
    axes[2, 0].set_title('City Extent and Wage (Curves Up)')
    axes[2, 0].set_xlabel('Wage')
    axes[2, 0].set_ylabel('City Extent')
    axes[2, 0].grid(True)

    # New plot 1R: workforce response to wage
    axes[2, 1].plot(wage, workers, color='purple')
    axes[2, 1].set_title('Workforce Response to Wage')
    axes[2, 1].set_xlabel('Wage')
    axes[2, 1].set_ylabel('Workers')
    axes[2, 1].grid(True)
    
    plt.tight_layout()
    st.pyplot(fig)

def display_files():
    # Get the list of run IDs
    folder_path = os.path.join('output_data', 'runs')
    file_path   = "run_metadata.yaml"
    run_ids     = get_run_ids(folder_path   )

    # Display dropdown to select run ID
    selected_run_id = st.selectbox("Select Run ID", run_ids)

    # Load data based on selected run ID
    run_metadata           = load_metadata(selected_run_id, folder_path, file_path)
    agent_out, model_out   = load_data(selected_run_id)

    # Display the metadata
    st.subheader("Metadata")
    st.write(run_metadata)

    # # TODO what does this do?
    # if agent_out is not None and model_out is not None:
    #     # Display loaded data
    #     st.subheader("Agent Data")
    #     st.dataframe(agent_out)

    #     st.subheader("Model Data")  
    #     st.dataframe(model_out)

    return agent_out, model_out

def load_data(run_id):
    agent_file = f"{run_id}_agent.csv"
    model_file = f"{run_id}_model.csv"

    if os.path.exists(agent_file) and os.path.exists(model_file):
        agent_out = pd.read_csv(agent_file)
        model_out = pd.read_csv(model_file)
        return agent_out, model_out
    else:
        return None, None

def load_metadata(run_id, folder_path, file_path):
    metadata_file = os.path.join(folder_path, file_path)

    with open(metadata_file, "r") as file:
        metadata = yaml.safe_load(file)

    run_metadata = metadata.get(run_id)
    return run_metadata

def get_run_ids(folder_path):
    file_names = os.listdir(folder_path)
    run_ids    = set()

    for file_name in file_names:
        if file_name.endswith("_agent.csv"):
            run_id = file_name.replace("_agent.csv", "")
            run_ids.add(run_id)

    return list(run_ids)

def main():
    num_steps  = st.sidebar.slider("Number of Steps", min_value=1, max_value=100, value=10)

    parameters = {
        'width':  10,
        'height': 10,
        'subsistence_wage': st.sidebar.slider("Subsistence Wage", min_value=30000., max_value=50000., value=40000., step=1000.),
        'working_periods':  st.sidebar.slider("Working Periods", min_value=30, max_value=50, value=40),
        'savings_rate':     st.sidebar.slider("Savings Rate", min_value=0.1, max_value=0.5, value=0.3, step=0.05),
        'r_prime':          st.sidebar.slider("R Prime", min_value=0.03, max_value=0.07, value=0.05, step=0.01)
    }

    agent_out, model_out = run_simulation(num_steps, parameters) # num_steps, subsistence_wage, working_periods, savings_rate, r_prime)
    
    st.title("Housing Market Model Output")
    plot_output(agent_out, model_out)
    
    st.markdown("---")
    st.header("Explore Existing Run Data")
    agent_out, model_out = display_files()

if __name__ == "__main__":
    main()