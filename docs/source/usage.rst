Usage
=====

You can start with this snippet of code

.. code-block:: python

    from probe_station import Dataset as DS
    import matplotlib.pyplot as plt
    ds = DS(
        r"path\to\data.data",
    )
    df = ds.dataframes[1]
    plt.plot(df["Voltages"], df["CurrentP"] - df["CurrentC"],