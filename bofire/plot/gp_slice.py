from typing import Optional, List, Tuple

from bofire.data_models.domain.api import Domain
from bofire.data_models.surrogates.api import SingleTaskGPSurrogate
from bofire.data_models.features.api import ContinuousInput, ContinuousOutput

import numpy as np
import pandas as pd

import plotly.graph_objects as go

def plot_gp_slice_plotly(
    domain: Domain,
    model: SingleTaskGPSurrogate,
    fixed_input_features: pd.Series,
    input_features: List[str],
    output_feature: str,
    resolution: Optional[int] = 100,
    observed_data: Optional[pd.DataFrame] = None,
) -> Tuple[go.Figure, go.Figure]:
    """
    Plot a slice of the Gaussian Process model.
    Where all but two input features are fixed, the other two input features are varied and gp predictions of the output features are plotted.
    If observed data is provided it is plotted in the mean prediction plot with a distinction between data points in the slice and data points not in the slice.

    Args:
        domain: The domain of the model.
        model: The surrogate model.
        fixed_input_features: The fixed input features.
        input_features: The two input features to vary.
        output_feature: The output feature to plot.
        resolution: The resolution of the meshgrid.
        observed_data: The observed data. 

    Returns:
        A plotly figure showing the mean prediction of the slice.
        A plotly figure showing the standard deviation of the slice.
    """
    # check if the fixed input features are in the domain
    for feature in fixed_input_features.keys():
        assert feature in domain.inputs.get_keys(), f"Feature {feature} not in domain inputs"

    # check if the input features are in the domain
    for feature in input_features:
        assert feature in domain.inputs.get_keys(), f"Feature {feature} not in domain inputs"
    
    # check if the output feature is in the domain
    assert output_feature in domain.outputs.get_keys(), f"Feature {output_feature} not in domain outputs"

    # check if the input features are continuous
    for feature in input_features:
        input_feature = domain.inputs.get_by_key(feature)
        assert isinstance(input_feature, ContinuousInput), f"Feature {feature} is not a ContinuousInput, we only support ContinuousInput features for now"

    # check if the output feature is continuous
    output = domain.outputs.get_by_key(output_feature)
    assert isinstance(output, ContinuousOutput), f"Feature {output_feature} is not a ContinuousOutput, we only support ContinuousOutput features for now"

    # check if the domain features are in the observed data
    if observed_data is not None:
        for feature in fixed_input_features.keys():
            assert feature in observed_data.columns, f"Feature {feature} not in observed data"

        for feature in input_features:
            assert feature in observed_data.columns, f"Feature {feature} not in observed data"

        assert output_feature in observed_data.columns, f"Feature {output_feature} not in observed data"

    
    x1 = np.linspace(domain.inputs.get_by_key(input_features[0]).bounds[0], domain.inputs.get_by_key(input_features[0]).bounds[1], resolution)
    x2 = np.linspace(domain.inputs.get_by_key(input_features[1]).bounds[0], domain.inputs.get_by_key(input_features[1]).bounds[1], resolution)

    X, Y = np.meshgrid(x1, x2)

    # now we need to create a dataframe with the meshgrid values
    samples = pd.DataFrame({input_features[0]: X.flatten(), input_features[1]: Y.flatten()}, index=range(resolution**2))

    # add the row to the samples dataframe
    rows = pd.DataFrame([fixed_input_features]*len(samples), index=range(resolution**2))

    # add the row to the samples dataframe
    samples = pd.concat([samples, rows], axis=1)

    # now predict the output
    y = model.predict(samples)
    output_pred = y[f"{output_feature}_pred"]
    output_sd = y[f"{output_feature}_sd"]


    # if observed data is provided, check for the lowest and highest value of the output feature in the observed data and the predicted data
    if observed_data is not None:
        output_min = min(output_pred.min(), observed_data[output_feature].min())
        output_max = max(output_pred.max(), observed_data[output_feature].max())
    else:
        output_min = output_pred.min()
        output_max = output_pred.max()

    # create a plot for the mean prediction
    fig = go.Figure()

    fig.add_trace(go.Contour(
        x=X.flatten(),
        y=Y.flatten(),
        z=output_pred,
        zmin=output_min,
        zmax=output_max,
        colorscale='Viridis',
        showscale=True,
        opacity=0.8,
        contours=dict(
            showlabels=True,
            labelfont=dict(
                family='Raleway',
                size=12,
                color='white',
            )
        ),
    ))

    # if observed data is provided, add the observed data to the plot
    if observed_data is not None:
        # check if there are datapoints that match the fixed input features
        mask = observed_data[fixed_input_features.keys()] == fixed_input_features
        mask = mask.all(axis=1)
        observed_data_in_slice = observed_data[mask]

        fig.add_trace(go.Scatter(
            x=observed_data_in_slice[input_features[0]],
            y=observed_data_in_slice[input_features[1]],
            mode='markers',
            marker=dict(
                size=8,
                color='red',
                symbol='circle-open'
            ),
            name='Observed data in slice',
            showlegend=True,
            hoverinfo='text',
            text=[f"Index: {index}<br>" + "<br>".join([f"{key}: {row[key]}" for key in fixed_input_features.keys()]) + f"<br>{input_features[0]}: {row[input_features[0]]}<br>{input_features[1]}: {row[input_features[1]]}<br>{output_feature}: {row[output_feature]}" for index, row in observed_data_in_slice.iterrows()]
        ))

        # repeat for the datapoints not in the slice
        observed_data_not_in_slice = observed_data[~mask]

        fig.add_trace(go.Scatter(
            x=observed_data_not_in_slice[input_features[0]],
            y=observed_data_not_in_slice[input_features[1]],
            mode='markers',
            marker=dict(
            size=8,
            color=observed_data_not_in_slice[output_feature],
            cmin=output_min,
            cmax=output_max,
            colorscale='Viridis',
            symbol='cross'
            ),
            name='Observed data not in slice',
            showlegend=True,
            hoverinfo='text',
            text=[
            f"Index: {index}<br>" + "<br>".join([f"{key}: {row[key]}" for key in fixed_input_features.keys()]) +
            f"<br>{input_features[0]}: {row[input_features[0]]}<br>{input_features[1]}: {row[input_features[1]]}<br>{output_feature}: {row[output_feature]}"
            for index, row in observed_data_not_in_slice.iterrows()
            ]
        ))

    fig.update_xaxes(title_text=input_features[0], range=[x1.min() - 0.01 * (x1.max() - x1.min()), x1.max() + 0.01 * (x1.max() - x1.min())])
    fig.update_yaxes(title_text=input_features[1], range=[x2.min() - 0.01 * (x2.max() - x2.min()), x2.max() + 0.01 * (x2.max() - x2.min())])

    # set title of plot with the output features and fixed input features
    title = f"{output_feature} slice with fixed features: " + ", ".join([f"{key}={value:.2f}" for key, value in fixed_input_features.items()])
    fig.update_layout(title=title, legend=dict(yanchor="top", y=-0.2, xanchor="left", x=0.01))

    # repeat for the standard deviation
    fig_sd = go.Figure()

    fig_sd.add_trace(go.Contour(
        x=X.flatten(),
        y=Y.flatten(),
        z=output_sd,
        zmin=0,
        zmax=output_sd.max(),
        colorscale='Viridis',
        showscale=True,
        opacity=0.8,
        contours=dict(
            showlabels=True,
            labelfont=dict(
                family='Raleway',
                size=12,
                color='white',
            )
        ),
    ))

    # if observed data is provided, add the observed data to the plot
    if observed_data is not None:
        # check if there are datapoints that match the fixed input features
        mask = observed_data[fixed_input_features.keys()] == fixed_input_features
        mask = mask.all(axis=1)
        observed_data_in_slice = observed_data[mask]

        fig_sd.add_trace(go.Scatter(
            x=observed_data_in_slice[input_features[0]],
            y=observed_data_in_slice[input_features[1]],
            mode='markers',
            marker=dict(
                size=8,
                color='red',
                symbol='circle-open'
            ),
            name='Observed data in slice',
            showlegend=True,
            hoverinfo='text',
            text=[f"Index: {index}<br>" + "<br>".join([f"{key}: {row[key]}" for key in fixed_input_features.keys()]) + f"<br>{input_features[0]}: {row[input_features[0]]}<br>{input_features[1]}: {row[input_features[1]]}<br>{output_feature}: {row[output_feature]}" for index, row in observed_data_in_slice.iterrows()]
        ))

    # set title
    title = f"{output_feature} standard deviation slice with fixed features: " + ", ".join([f"{key}={value:.2f}" for key, value in fixed_input_features.items()])
    fig_sd.update_layout(title=title, legend=dict(yanchor="top", y=-0.2, xanchor="left", x=0.01))

    # set x and y axis titles
    fig_sd.update_xaxes(title_text=input_features[0], range=[x1.min() - 0.01 * (x1.max() - x1.min()), x1.max() + 0.01 * (x1.max() - x1.min())])
    fig_sd.update_yaxes(title_text=input_features[1], range=[x2.min() - 0.01 * (x2.max() - x2.min()), x2.max() + 0.01 * (x2.max() - x2.min())])

    return fig, fig_sd