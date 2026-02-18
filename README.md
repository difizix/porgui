Temporary private repo for sharing usage examples of `image3kit` python package

## Usage

* Setup venv:
```
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### Current Examples

* [dering_segment.py](./dering_segment.py)
    * Illustrates how to create new filters using NumPy: `desharpen` function
    * Illustrates use of dering filter (rather flimsy -- difficult to get its parameters right)
    * `segment2` function (do not use this in production, does not work well, unless you are willing to improve it!)
    * Plotting / screenshots

* run dering_segment.py:
```
.venv/bin/python  dering_segment.py  volume_467x1775x1480.raw
```

* [ik_vtk_utils.py](./ik_vtk_utils.py)
    - Using VTK for offscreen 3D visualisation
    - For now you got to edit ik_vtk_utils.py and and set the threshold and filename
```
python  ik_vtk_utils.py  <IMAGE_NAME>.am/_NXxNYxNZ.raw/.tif/.mhd
```

### TODO

* Integrate with OpenFoam/GeoChemFoam

### CONTRIBUTING

Please let me know beforehand and I will make this repo more professional.

The `image3kit` pip package lacks proper documentation, but you can clone the [image3kit] repository and use LLMs for help!



> [!CAUTION]
> The original author will submit draft commits to the `main` branch directly, and overwrites the git history!, unless someone else starts pushing git commits.


<!-- References -->

[image3kit]: https://github.com/digiporflow/image3kit
