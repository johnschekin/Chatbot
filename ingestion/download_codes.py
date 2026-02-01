"""
NYC Building Codes PDF Downloader
=================================
Downloads all 2022 NYC Construction Code PDFs from nyc.gov.

How it works:
1. Lists all PDF filenames for each code type
2. Downloads each PDF from the NYC.gov server
3. Saves them organized by code type in folders
"""

import os
import requests
import time
from pathlib import Path

# Base URL for PDFs (direct download)
BASE_URL = "https://www.nyc.gov/assets/buildings/pdf/"

# Output directory
OUTPUT_DIR = Path(__file__).parent / "pdfs"

# All PDF files organized by code type
PDF_FILES = {
    "GAP_General_Administrative": [
        "2022GAP_Chapter1_AdministrationWBwm.pdf",
        "2022GAP_Chapter2_EnforcementWBwm.pdf",
        "2022GAP_Chapter3_MaintenanceWBwm.pdf",
        "2022GAP_Chapter4_LicensingWBwm.pdf",
        "2022GAP_Chapter5_MiscellaneousWBwm.pdf",
    ],
    "PC_Plumbing_Code": [
        "2022PC_Chapter1_AdministrationWBwm.pdf",
        "2022PC_Chapter2_DefinitionsWBwm.pdf",
        "2022PC_Chapter3_GenRegsWBwm.pdf",
        "2022PC_Chapter4_FixturesWBwm.pdf",
        "2022PC_Chapter5_WaterHeatersWBwm.pdf",
        "2022PC_Chapter6_WaterSupplyWBwm.pdf",
        "2022PC_Chapter7_SanitaryDrainageWBwm.pdf",
        "2022PC_Chapter8_IndirectWasteWBwm.pdf",
        "2022PC_Chapter9_VentsWBwm.pdf",
        "2022PC_Chapter10_TrapsWBwm.pdf",
        "2022PC_Chapter11_StormDrainageWBwm.pdf",
        "2022PC_Chapter12_SpecialPipingWBwm.pdf",
        "2022PC_Chapter13_NonpotableWaterWBwm.pdf",
        "2022PC_Chapter14_SubsurfaceIrrigationWBwm.pdf",
        "2022PC_Chapter15_RefStandardsWBwm.pdf",
        "2022PC_AppendixA_ReservedWBwm.pdf",
        "2022PC_AppendixB_ReservedWBwm.pdf",
        "2022PC_AppendixC_StructuralSafetyWBwm.pdf",
        "2022PC_AppendixD_ReservedWBwm.pdf",
        "2022PC_AppendixE_WaterPipingWBwm.pdf",
    ],
    "MC_Mechanical_Code": [
        "2022MC_Chapter1_AdministrationWB.pdf",
        "2022MC_Chapter2_DefinitionsWB.pdf",
        "2022MC_Chapter3_GenRegsWB.pdf",
        "2022MC_Chapter4_VentilationWB.pdf",
        "2022MC_Chapter5_ExhaustWB.pdf",
        "2022MC_Chapter6_DuctsWB.pdf",
        "2022MC_Chapter7_CombustionAirWB.pdf",
        "2022MC_Chapter8_ChimneysVentsWB.pdf",
        "2022MC_Chapter9_SpecificAppliancesWB.pdf",
        "2022MC_Chapter10_BoilersWB.pdf",
        "2022MC_Chapter11_RefrigerationWB.pdf",
        "2022MC_Chapter12_HydronicPipingWB.pdf",
        "2022MC_Chapter13_FuelOilPipingWB.pdf",
        "2022MC_Chapter14_SolarSystemsWB.pdf",
        "2022MC_Chapter15_RefStandardsWB.pdf",
        "2022MC_AppendixA_ChimneyConnectorWB.pdf",
        "2022MC_AppendixB_ReservedWB.pdf",
        "2022MC_AppendixC_FuelOilStorageWB.pdf",
    ],
    "FGC_Fuel_Gas_Code": [
        "2022FGC_Chapter1_AdministrationWB.pdf",
        "2022FGC_Chapter2_DefinitionsWB.pdf",
        "2022FGC_Chapter3_GenRegsWB.pdf",
        "2022FGC_Chapter4_GasPipingWB.pdf",
        "2022FGC_Chapter5_ChimneysVentsWB.pdf",
        "2022FGC_Chapter6_SpecAppliancesWB.pdf",
        "2022FGC_Chapter7_GaseousHydrogenWB.pdf",
        "2022FGC_Chapter8_RefStandardsWB.pdf",
        "2022FGC_AppendixA_ReservedWB.pdf",
        "2022FGC_AppendixB_ReservedWB.pdf",
        "2022FGC_AppendixC_ReservedWB.pdf",
        "2022FGC_AppendixD_ReservedWB.pdf",
        "2022FGC_AppendixE_GasServiceWB.pdf",
        "2022FGC_AppendixF_ReservedWB.pdf",
        "2022FGC_AppendixG_HPNaturalGasWB.pdf",
    ],
    "BC_Building_Code": [
        "2022BC_Chapter01_AdministrationWBwm.pdf",
        "2022BC_Chapter02_DefinitionsWBwm.pdf",
        "2022BC_Chapter03_OccupancyClassWBwm.pdf",
        "2022BC_Chapter04_SpecialUseWBwm.pdf",
        "2022BC_Chapter05_HeightAreaWBwm.pdf",
        "2022BC_Chapter06_ConstructionTypeWBwm.pdf",
        "2022BC_Chapter07_FireResistanceWBwm.pdf",
        "2022BC_Chapter08_InteriorFinishesWBwm.pdf",
        "2022BC_Chapter09_FireProtectionWBwm.pdf",
        "2022BC_Chapter10_EgressWBwm.pdf",
        "2022BC_Chapter11_AccessibilityWBwm.pdf",
        "2022BC_Chapter12_InteriorEnvironmentWBwm.pdf",
        "2022BC_Chapter13_EnergyWBwm.pdf",
        "2022BC_Chapter14_ExteriorWallsWBwm.pdf",
        "2022BC_Chapter15_RoofsRooftopsWBwm.pdf",
        "2022BC_Chapter16_StructuralDesignWBwm.pdf",
        "2022BC_Chapter17_SpecialInspectionsWBwm.pdf",
        "2022BC_Chapter18_SoilsFoundationsWBwm.pdf",
        "2022BC_Chapter19_ConcreteWBwm.pdf",
        "2022BC_Chapter20_AluminimWBwm.pdf",
        "2022BC_Chapter21_MasonryWBwm.pdf",
        "2022BC_Chapter22_SteelWBwm.pdf",
        "2022BC_Chapter23_WoodWBwm.pdf",
        "2022BC_Chapter24_GlassGlazingWBwm.pdf",
        "2022BC_Chapter25_GypsumBoardWBwm.pdf",
        "2022BC_Chapter26_PlasticWBwm.pdf",
        "2022BC_Chapter27_ElectricalWBwm.pdf",
        "2022BC_Chapter28_MechanicalWBwm.pdf",
        "2022BC_Chapter29_PlumbingWBwm.pdf",
        "2022BC_Chapter30_ElevatorsWBwm.pdf",
        "2022BC_Chapter31_SpecConstructionWBwm.pdf",
        "2022BC_Chapter32_PublicRightofWayWBwm.pdf",
        "2022BC_Chapter33_Con_DemoSafetyWBwm.pdf",
        "2022BC_Chapter34_ReservedWBwm.pdf",
        "2022BC_Chapter35_RefStandardsWBwm.pdf",
        "2022BC_AppendixA_ReservedWBwm.pdf",
        "2022BC_AppendixB_ReservedWBwm.pdf",
        "2022BC_AppendixC_ReservedWBwm.pdf",
        "2022BC_AppendixD_FireDistrictsWBwm.pdf",
        "2022BC_AppendixE_SuppAccessibilityWBwm.pdf",
        "2022BC_AppendixF_Rodent-ProofingWBwm.pdf",
        "2022BC_AppendixG_FloodResistantWBwm.pdf",
        "2022BC_AppendixH_OutdoorSignsWBwm.pdf",
        "2022BC_AppendixI_ReservedWBwm.pdf",
        "2022BC_AppendixJ_ReservedWBwm.pdf",
        "2022BC_AppendixK_ElevatorStandardsWBwm.pdf",
        "2022BC_AppendixL_ReservedWBwm.pdf",
        "2022BC_AppendixM_One-TwoWBwm.pdf",
        "2022BC_AppendixN_AssistiveListeningWBwm.pdf",
        "2022BC_AppendixO_ReservedWBwm.pdf",
        "2022BC_AppendixP_ReservedWBwm.pdf",
        "2022BC_AppendixQ_FireStandardsWBwm.pdf",
        "2022BC_AppendixR_AcousticalTileWBwm.pdf",
        "2022BC_AppendixS_ExitPathMarkingsWBwm.pdf",
        "2022BC_AppendixU_AncillaryDwellingWBwm.pdf",
    ],
}


def download_pdf(filename: str, output_path: Path) -> bool:
    """Download a single PDF file."""
    url = BASE_URL + filename

    try:
        print(f"  Downloading: {filename}...", end=" ", flush=True)
        response = requests.get(url, timeout=60)

        if response.status_code == 200:
            output_path.write_bytes(response.content)
            size_mb = len(response.content) / (1024 * 1024)
            print(f"OK ({size_mb:.1f} MB)")
            return True
        else:
            print(f"FAILED (HTTP {response.status_code})")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Download all NYC building code PDFs."""
    print("=" * 60)
    print("NYC Building Codes PDF Downloader")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_files = sum(len(files) for files in PDF_FILES.values())
    downloaded = 0
    failed = 0

    print(f"\nTotal PDFs to download: {total_files}")
    print(f"Output directory: {OUTPUT_DIR}\n")

    for code_type, files in PDF_FILES.items():
        print(f"\n[{code_type}] - {len(files)} files")
        print("-" * 40)

        # Create subdirectory for this code type
        code_dir = OUTPUT_DIR / code_type
        code_dir.mkdir(exist_ok=True)

        for filename in files:
            output_path = code_dir / filename

            # Skip if already downloaded
            if output_path.exists():
                print(f"  Skipping (exists): {filename}")
                downloaded += 1
                continue

            if download_pdf(filename, output_path):
                downloaded += 1
            else:
                failed += 1

            # Small delay to be respectful to the server
            time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"Download complete!")
    print(f"  Downloaded: {downloaded}/{total_files}")
    print(f"  Failed: {failed}")
    print(f"  Location: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
