import os
import shutil
from pathlib import Path

import image3kit as ik
import pnmkit as nm
from pnmkit.models import (
    FlowSim,
    VoxImg,
    get_color_gradxy,
    mSN,  # snm wrapper
    mXP,  # xpm wrapper
    plKr, # property: Kr
    plPc, # property: Pc
    plRI, # property: RI
    pSgr, # property: Sgr
)
from pnmkit.plots import plot_cycls, plot_props_compact, plot_si_sr


def runPlotPNMs(tmp_path, mtd):
    # Setup paths
    img_name = "Pak2D_240x200x1_5um.dat"
    img_path = Path(__file__).resolve().parent / img_name

    assert img_path.exists(), f"Image {img_path} not found"

    os.chdir(tmp_path)

    # 1. Image processing & Network Extraction
    # We follow the pattern in test_snflow_2d.py
    img = ik.VxlImgU8(img_path)
    for _ in range(2):
        img.grow_label(0)
    img.spacing = (1e-6, 1e-6, 1e-6)
    img.extrude_dist_map(offset=0.5, scale=2.0)
    img_name = f"Pak2DExtruded_{img.nx}x{img.ny}x{img.nz}_5p0um"
    img.write(f"{img_name}.raw")

    extract_params = {"OutputName": img_name, "Overwrite": "T", "VoidRange": "0 0"}
    if mtd != mXP:
        nm.mextract(img, extract_params)

        assert Path(f"{img_name}_ms.xmf").exists(), "Network extraction failed"

    print(f"pwd: {Path.cwd()},  image file: {img_name}")

    img_obj = VoxImg(img_name, netDir = str(tmp_path))

    inpt = {
        "UpscaleBox": "0.2 0.9",
        "InitContAng": "1 0 10 -0.2 -3. rand 0.",
        "NetworkDir": str(tmp_path),
        "Cycle2": "1. -1.0E+05 0.05 T T",
        "Cycle3": "0. 1.0E+05 0.05 T T",
        "Cycle1_BC": "T F F T DP 1. 1.",
        "Cycle2_BC": "T F F T DP 1. 1.",
        "Cycle3_BC": "T F F T DP 1. 1.",
        "AlterContAng": "4 30 50 -0.2 -3. rand 0.",
        "Overwrite": "T"
    }

    clrSchem = get_color_gradxy()

    # Simplified CAs and Swis for faster test
    CAs = [[30, 50]]
    Swis = [0., 0.3]

    simsAll = []
    simsPc = []
    simsSw = []

    for jj, CAp in enumerate(CAs):
        simsSw.append([])
        for ii, Swi in enumerate(Swis):
            tag = f"C{CAp[0]}A{CAp[1]}Swi{Swi}"

            # FIXME these depend on `mtd`
            p = inpt.copy()
            p["AlterContAng"] = f"4 {CAp[0]} {CAp[1]} -0.2 -3. rand 0."
            p["Cycle1"] = f"{Swi} 1.0E+05 0.05 T T"

            sim = FlowSim(tag, f"Swi={Swi}, CA={CAp[0]}-{CAp[1]}", img_obj, mtd, clrSchem[0][ii], p)
            sim.tag = tag
            simsAll.append(sim)
            simsPc.append(sim)
            simsSw[jj].append(sim)

    # 3. Run Simulation
    for sim in simsAll:
        ret = sim.runSim("TestThread", forceRun=True) # run_xnflow or run_xpm
        assert ret == 0, f"Simulation failed for {sim.tag}" # ideally the runSim shall throw an exception instead for debugging

    # 4. Plotting & Verification, just checking if the files are created
    pltTag = mtd.name

    plot_props_compact(simsPc, [plPc], icycls=[1, 2], outfile=f"Test_{pltTag}_PcCmpct.svg", addSummary=False)
    assert Path(f"Test_{pltTag}_PcCmpct.svg").exists()

    plot_props_compact(simsPc, [plKr], icycls=[1, 2], outfile=f"Test_{pltTag}_KrCmpct.svg", addSummary=False)
    assert Path(f"Test_{pltTag}_KrCmpct.svg").exists()

    plot_cycls(simsPc, [plPc, plKr, plRI], icycls=[1, 2], outfile=f"Test_{pltTag}_PcKrRI.svg")
    assert Path(f"Test_{pltTag}_PcKrRI.svg").exists()

    # Test plot_si_sr
    plot_si_sr(simsSw, ["CA=30-50"], [pSgr], outfile=f"Test_{pltTag}_SiSr.svg")
    assert Path(f"Test_{pltTag}_SiSr.svg").exists()


if __name__ == "__main__":

    test_dir = Path(__file__).resolve().parent

    for mtd in [mSN, mXP]:
        tmp_path = test_dir / f"run_tst_{mtd.name}"
        try:
            print(f"Running {mtd.name} test...")
            shutil.rmtree(tmp_path, ignore_errors=True)
            tmp_path.mkdir(exist_ok=True)
            runPlotPNMs(Path(tmp_path), mtd)

            print(f"Done with test runPlotPNMs NOT cleaning up, {tmp_path}\n")
            # shutil.rmtree(tmp_path)
        except Exception as e:
            print(f"Error occurred: {e}")
            print(f"Temporary directory kept for debugging: {tmp_path}")
            raise
