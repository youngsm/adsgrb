from astropy import units as u, constants as const
from astropy.time import Time
import pandas as pd
import numpy as np
from .constants import flux_densities, ebv2A_b_df
import os.path
import re, glob2
from functools import reduce


def angstromToHz(ang: float):
    return (const.c / (ang * u.angstrom).to(u.m)).to(u.Hz).value


def ebv2A_b(grb: str, bandpass: str, ra="", dec=""):
    """ebv2A_b A function that returns the galactic extinction correction
                       at a given position for a given band.

                            This takes data from Schlegel, Finkbeiner & Davis (1998) in the form
                            of the SFD dust map, and is queried using the dustmaps python package.
                            Updated coefficient conversion values for the SFD is taken from Schlafly & Finkbeiner (2011)
                            and is found in SF11_conversions.txt.
    Args:
            ra (str): Right ascension
            dec (str): Declination
            bandpass (str): One of the 94 bandpasses supported. See SF11_conversion.txt for these bandpasses.

    Returns:
            float: Galactic extinction correct in magnitude.
    """

    from astropy.coordinates import SkyCoord
    from dustmaps.sfd import SFDQuery

    sfd = SFDQuery()

    if not (ra or dec):
        import astroquery.exceptions
        from astroquery.simbad import Simbad

        try:
            obj = Simbad.query_object(f"GRB {grb}")
            skycoord = SkyCoord("%s %s" % (obj["RA"][0], obj["DEC"][0]), unit=(u.hourangle, u.deg))
        except astroquery.exceptions.RemoteServiceError:
            raise astroquery.exceptions.RemoteServiceError(
                f"Couldn't find the position of GRB {grb}. Please supply in RA and DEC manually."
            )
    else:
        skycoord = SkyCoord("%s %s" % (ra, dec), frame="icrs", unit=(u.hourangle, u.deg))

    # this grabs the degree of reddening E(B-V) at the given position in the sky.
    # see https://astronomy.swin.edu.au/cosmos/i/interstellar+reddening for an explanation of what this is
    ebv = sfd(skycoord)

    # this factor is A_b / E(B-V)
    factor = ebv2A_b_df["3.1"][bandpass]

    A_b = ebv * factor

    return A_b  # [mag]


def toFlux(
    mag: float,
    band: str,
    grb: str,
    magerr: float = 0,
    photon_index: float = 0,
    photon_index_err: float = 0,
    A_b: float = 0,
    source: str = "manual",
    ra: str = "",
    dec: str = "",
):

    band = re.sub(r"(\'|_|\\|\(.+\))", "", band)
    band = re.sub(r"(?<![A-Za-z])([mw]\d{1})", r"uv\1", band)
    if source == "uvot":
        band += "_swift"
    band = band if band != "v" else "V"

    # determine index type for conversion of f_nu to R band
    beta = photon_index - 1

    try:
        lambda_R, *__ = flux_densities["R"]  # lambda_R in angstrom
        lambda_x, f_x, bandpass_for_ebv = flux_densities[band]
    except KeyError:
        raise KeyError(f"Band '{band}' is not currently supported.")

    # get correction for galactic extinction to be added to magnitude if not already supplied
    if A_b == 0:
        A_b = ebv2A_b(grb, bandpass_for_ebv, ra=ra, dec=dec)

    # convert from flux density in another band to R!
    f_R = f_x * (lambda_x / lambda_R) ** (-beta)
    f_lam_or_nu = f_R

    if band.lower() in ["u_swift", "b_swift", "v_swift", "uvw1_swift", "uvw2_swift", "uvm2_swift", "white"]:
        # If flux density is given as f_lambda (erg / cm2 / s / Å)
        lam_or_nu = lambda_R * (u.angstrom)
        f_lam_or_nu = f_lam_or_nu * (u.erg / u.cm ** 2 / u.s / u.angstrom)
    else:
        # If flux density is given as f_nu (erg / cm2 / s / Hz)
        lam_or_nu = angstromToHz(lambda_R) * (u.Hz)
        f_lam_or_nu = f_lam_or_nu * (u.erg / u.cm ** 2 / u.s / u.Hz)

    flux = (lam_or_nu * f_lam_or_nu * 10 ** (-(mag + A_b) / 2.5)).value

    # see https://youngsam.me/files/error_prop.pdf for derivation
    fluxerr = abs(flux) * np.sqrt(
        (magerr * np.log(10 ** (0.4))) ** 2 + (photon_index_err * np.log(lambda_x / lambda_R)) ** 2
    )

    assert flux >= 0, "Error computing flux."
    assert fluxerr >= 0, "Error computing flux error."
    return flux, fluxerr


# main conversion function to call
def convertGRB(
    GRB: str, battime: str = "", index: float = 0, index_type: str = "", use_nick: bool = False, debug: bool = False
):
    # make sure we have dust maps downloaded for calculating galactic extinction
    _check_dust_maps()

    # assign column names and datatypes before importing
    dtype = {
        "date": str,
        "time": str,
        "exp": str,
        "mag": np.float64,
        "mag_err": np.float64,
        "band": str,
    }
    names = list(dtype.keys())
    if use_nick:
        names.insert(0, "nickname")  # add nickname column
        dtype["nickname"] = str  # add nickname type

    """ will import data using the following headers
    IF: use_nick = False
    | date | time | exp | mag | mag_err | band |
    OR
    IF: use_nick = True
    | nickname | date | time | exp | mag | mag_err | band |
    """

    # try to import magnitude table to convert
    try:
        global directory
        glob_path = reduce(os.path.join, (directory, "**", f"{GRB}.txt"))
        filename, *__ = glob2.glob(glob_path)
        mag_table = pd.read_csv(
            filename,
            delimiter=r"\t+|\s+",
            names=names,
            dtype=dtype,
            skiprows=1,
            engine="python",
        )

    except ValueError as error:
        raise error
    except IndexError as error:
        raise ImportError(message=f"Couldn't find GRB table at {filename}.")

    # grab photon index, trigger time, and position in sky of GRB
    if battime and index:
        starttime = Time(battime)
    else:
        try:
            bat_spec_df = pd.read_csv(
                os.path.join(directory, "trigs_and_specs.txt"),
                delimiter="\t+|\s+",
                index_col=0,
                header=0,
                engine="python",
            )
            bat_spec_df["photon_index"] = bat_spec_df["photon_index"].astype(np.float64)
            bat_spec_df["photon_index_err"] = bat_spec_df["photon_index_err"].astype(np.float64)
            bat_spec_df.dropna(how="any", subset=["photon_index", "photon_index_err"], inplace=True)
            photon_index, photon_index_err = list(bat_spec_df.loc[GRB, ["photon_index", "photon_index_err"]])
            battime = list(bat_spec_df.loc[GRB, ["trigger_date", "trigger_time"]])
            ra, dec = bat_spec_df.loc[GRB, ["ra", "dec"]]
            battime = " ".join(battime)
            starttime = Time(battime)

        except KeyError:
            raise ImportError(
                f"{GRB} isn't currently supported and it's trigger time, photon index, and position must be manually provided. :("
            )

    converted = {k: [] for k in ("time_sec", "flux", "flux_err", "band")}
    if debug:
        converted_debug = {k: [] for k in ("time_sec", "flux", "flux_err", "band", "logF", "logT", "mag", "mag_err")}

    for __, row in mag_table.iterrows():
        band = row["band"]
        magnitude = row["mag"]
        mag_err = row["mag_err"]

        # attempt to convert a single magnitude to flux given a band, position in the sky, mag_err, and photon index
        try:
            flux, flux_err = toFlux(
                magnitude, band, ra, dec, mag_err, photon_index=photon_index, photon_index_err=photon_index_err
            )
        except KeyError as error:
            print(error)
            continue

        # convert UT to a time delta since trigger time
        date_UT = row["date"]
        time_UT = row["time"]
        time_UT = f"{date_UT} {time_UT}"
        astrotime = Time(time_UT, format="iso")  # using astropy Time package
        dt = astrotime - starttime  # for all other times, subtract start time
        time_sec = round(dt.sec, 5)  # convert delta time to seconds

        converted["time_sec"].append(time_sec)
        converted["flux"].append(flux)
        converted["flux_err"].append(flux_err)
        converted["band"].append(band)

        # verbosity if you want it
        if debug:
            logF = np.log10(flux)
            logT = np.log10(time_sec)
            converted_debug["time_sec"].append(time_sec)
            converted_debug["flux"].append(flux)
            converted_debug["flux_err"].append(flux_err)
            converted_debug["band"].append(band)
            converted_debug["logF"].append(logF)
            converted_debug["logT"].append(logT)
            converted_debug["mag"].append(magnitude)
            converted_debug["mag_err"].append(mag_err)

    # after converting everything, go from dictionary -> DataFrame -> csv!
    if not debug:
        save_path = os.path.join(os.path.dirname(filename), f"{GRB}_converted_flux.txt")
        pd.DataFrame.from_dict(converted).to_csv(save_path, sep="\t", index=False)
    else:
        save_path = os.path.join(os.path.dirname(filename), f"{GRB}_converted_flux_DEBUG.txt")
        pd.DataFrame.from_dict(converted_debug).to_csv(save_path, sep="\t", index=False)

    return


# small setter to set the main conversion directory
def set_dir(dir):
    global directory
    directory = os.path.abspath(dir)
    return directory


# getter to return conversion directory
def get_dir():
    global directory
    return directory


# Converts all magnitude tables that are in the path format of
# get_dir()/*_flux/<GRB>.txt
def convert_all(debug=False):
    # grab all filepaths for LCs in magnitude
    filepaths = glob2.glob(reduce(os.path.join, (get_dir(), "*_flux", "*.txt")))
    grbs = [
        os.path.split(f)[1][:-4]
        for f in filepaths
        if os.path.split(f)[1].count("flux") == 0 and "trigger" not in f and "spectral_index" not in f
    ]

    converted = []
    unsupported = 0
    unsupported_names = []
    pts_skipped = 0
    for GRB in grbs:
        try:
            convertGRB(GRB, debug=debug)
            converted.append(GRB)
        except ImportError as error:
            unsupported += 1
            unsupported_names.append(GRB)
            print(error)
            pass
        except KeyError as error:
            pts_skipped += 1
            print(str(error).strip('"'))
            pass
        except Exception as error:
            print(GRB)
            raise error

    print(
        "\n" + "=" * 30 + "\nStats\nUnsupported:",
        unsupported,
        "\nTotal:",
        len(grbs),
        "\nSuccessfully Converted:",
        len(converted),
        "\nPoints skipped",
        pts_skipped,
    )

    with open(os.path.join(get_dir(), "unsupported.txt"), "w") as f:
        f.write("\n".join(unsupported_names))


# simple checker that downloads the SFD dust map if it's not already there
def _check_dust_maps():
    from dustmaps.config import config
    import dustmaps.sfd

    data_dir = os.path.join(os.path.dirname(__file__), "extinction_maps")
    if not os.path.exists(os.path.join(data_dir, "sfd")):
        config["data_dir"] = data_dir
        dustmaps.sfd.fetch()


# sets directory to the current working directory, or whatever folder you're currently in
directory = os.getcwd()
