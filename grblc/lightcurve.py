# standard libs
import os
import re
import sys

# third party libs
import numpy as np
import pandas as pd
import plotly.express as px

# custom modules
from .util import get_dir
from .io import read_data, convert_data
from .photometry.convert import _convertGRB, _host_kcorrectGRB
from .evolution.colorevol import _colorevolGRB
from .evolution.rescale import _rescaleGRB


class Lightcurve: # define the object Lightcurve
    _name_placeholder = "unknown grb" # assign the name for GRB if not provided


    def __init__(
        self,
        grb: str = None,
        ra: str = None,
        dec: str = None,
        path: str = None,
        data_space: str = 'lin',
        appx_bands: bool = True,
        remove_outliers: bool = False, 
        save_in_folder = None,
    ):
        """
        Function to set the `xdata` and `ydata`, and optionally `xerr` and `yerr` of the lightcurve.
        Reads in data from a file. The data must be in the correct format.
        See the :py:meth:`io.read_data` for more information.

        Parameters:
        -----------
        - grb: str: GRB name.
        - ra: str: Right ascension of GRB.
        - dec: str: Declination of GRB.
        - path: str: Path to the magnitude file. 
        - data_space : str, {log, lin}: Whether to convert the data to logarithmic or linear space, by default 'lin'.
        - appx_bands: bool: If True, approximates certain bands, e.g. u' approximated to u, etc.
                            See the :py:meth:`io.convert_data` for more information.
        - remove_outliers: bool: If True, removes outliers identified in our analysis, by default False. 
                                See Dainotti et al. (2024).

        Returns:
        --------
        - None

        Raises:
        -------
        - AssertionError: If either grb or location is not provided.
        - AssertionError: If only limiting magnitudes are present.
        
        """

        # Assertion
        assert bool(grb and ra and dec), "Must provide either grb name or location."

        # some default conditions for the name of GRBs and the path of the data file
        if grb:
            self.name = grb 
            # asserting the name of the GRB

        else:
            self.name = self._name_placeholder  
            # asserting the name of the GRB as 'Unknown GRB' if the name is not provided

        if ra:
            self.ra = ra

        if dec:
            self.dec = dec

        if save_in_folder is not None:
            self.main_dir = self.name+"/"
            if not os.path.exists(self.main_dir):
                os.mkdir(self.main_dir)

        if isinstance(path, str):
            self.path = path  # asserting the path of the data file
            self._set_data(data_space, appx_bands, remove_outliers) #, data_space='lin') # reading the data from a file
            print(self.df.head())


    def _set_data(
        self, 
        data_space: str ='lin',
        appx_bands: bool =True, 
        remove_outliers: bool =False
    ): 
        """
        Function to set the data.
        
        """

        # reads the data, sorts by time, excludes negative time
        df = read_data(self.path, data_space) 
        
        # initialising a new column
        df.insert(4, "band_appx", "") 

        # asserting those data points only which does not have limiting nagnitude
        df = df[df['mag_err'] != 0] 
        assert len(df)!=0, "Only limiting magnitudes present."

        # initialising data to self
        self.xdata = df["time_sec"].to_numpy()  
            # passing the time in sec as a numpy array in the x column of the data

        self.ydata = df["mag"].to_numpy() 
            # passing the magnitude as a numpy array in the y column of the data

        self.yerr = df["mag_err"].to_numpy()  
            # passing the magnitude error as an numpy array y error column of the data

        self.band_original = df["band"].to_list() 
            # passing the original bands (befotre approximation of the bands) as a list
        
        if appx_bands:
            self.band = df["band_appx"] = convert_data(df["band"]) 
            # passing the reassigned bands (after the reapproximation of the bands) as a list
        
        else:
            self.band = self.band_original

        self.system = df["system"].to_list()  # passing the filter system as a list
        
        self.telescope = df["telescope"].to_list() 
            # passing the telescope name as a list
        
        self.extcorr = df["extcorr"].to_list()  
            # passing the galactic extinction correction detail (if it is corrected or not) as a list
        
        self.source = df["source"].to_list()  
            # passing the source from where the particular data point has been gathered as a list
        
        try:
            self.flag = df["flag"].to_list()
        
        except:
            self.flag = None

        if remove_outliers:
            df = df[df.flag == 'no']

        self.df = df  # passing the whole data as a data frame


    def convertGRB(
        self,
        save: bool = True,
        debug: bool = False
    ):
        """
        Function to convert magnitudes to the AB system and correct for galactic extinction.
        This is an optional step. If the files are already converted, can skip this.

        Parameters:
        -----------
        - self: The Lightcurve object should be initialised to call correctGRB().
        - save: bool: If True, saves converted file.
        - debug: bool: More information saved for debugging the conversion. By default, False.

        Returns:
        --------
        - Converted magnitude tab-separated '.txt'.

        Raises:
        -------
        - KeyError: If the telescope and filter is not found.
        - ImportError: If the code can't find grb table at the given path.

        """

        save_in_folder = None
        if save:
            save_in_folder = self.main_dir + 'converted/'
            if not os.path.exists(save_in_folder):
                os.mkdir(save_in_folder)
        else:
            save_in_folder = None

        self.df = _convertGRB(
                            grb = self.name,
                            ra = self.ra,
                            dec = self.dec,
                            mag_table = self.df,
                            save_in_folder = save_in_folder,
                            debug = debug
                            )
        return self.df
        

    def displayGRB(
        self, 
        save_static: bool = False, 
        save_static_type: str = '.png', 
        save_interactive: bool = False, 
    ):
        """
        Function to create an interactive plot of magnitude lightcurve, excluding limiting magnitudes.

        Parameters:
        -----------
        save_static: bool: If True, saves static plot of magnitude lightcurve.
        save_static_type: str: By default, the static type is '.png'.
        save_interactive: bool: If True, saves '.html' plot of magnitude lightcurve.

        Returns:
        --------
        fig: plotly.Figure object: Interactive plot of magnitude lightcurve.

        """

        save_in_folder = None
        if save_static or save_interactive:
            save_in_folder = self.main_dir + 'plots/'
            if not os.path.exists(save_in_folder):
                os.mkdir(save_in_folder)

        fig = px.scatter(data_frame=self.df,
                    x=np.log10(self.xdata),
                    y=self.ydata,
                    error_y=self.yerr,
                    color=self.band,
                    color_discrete_sequence=px.colors.qualitative.Set1,
                    hover_data=['telescope', 'source'],
                )

        font_dict=dict(family='arial',
                    size=18,
                    color='black'
                    )
        title_dict=dict(family='arial',
                    size=20,
                    color='black'
                    )

        fig['layout']['yaxis']['autorange'] = 'reversed'
        fig.update_yaxes(title_text="<b>Magnitude<b>",
                        title_font_color='black',
                        title_font_size=20,
                        showline=True,
                        showticklabels=True,
                        showgrid=False,
                        linecolor='black',
                        linewidth=2.4,
                        ticks='outside',
                        tickfont=font_dict,
                        mirror='allticks',
                        tickwidth=2.4,
                        tickcolor='black',
                        )

        fig.update_xaxes(title_text="<b>log10 Time (s)<b>",
                        title_font_color='black',
                        title_font_size=20,
                        showline=True,
                        showticklabels=True,
                        showgrid=False,
                        linecolor='black',
                        linewidth=2.4,
                        ticks='outside',
                        tickfont=font_dict,
                        mirror='allticks',
                        tickwidth=2.4,
                        tickcolor='black',
                        )

        fig.update_layout(title="GRB " + self.name,
                        title_font_size=24,
                        font=font_dict,
                        legend = dict(font = font_dict),
                        legend_title = dict(text= "<b>Bands<b>", font=title_dict),
                        plot_bgcolor='white',
                        width=960,
                        height=540,
                        margin=dict(l=40,r=40,t=50,b=40)
                        )

        if save_static:
            fig.write_image(save_in_folder+self.name+save_static_type)

        if save_interactive:
            fig.write_html(save_in_folder+self.name+'.html')

        return fig


    def colorevolGRB(
        self, 
        chosenfilter: str ='mostnumerous', 
        print_status: bool =True, 
        return_rescaledf: bool =False,
        save: bool = False, 
        debug: bool =False
    ):

        """
        Function performs the colour evolution analysis (see Section 3.3 of Dainotti et al. (2024) https://arxiv.org/abs/2405.02263) 
        
        Parameters:
        -----------
        - self, 
        - chosenfilter: str ='mostnumerous', 
        - print_status: bool =True, 
        - save: bool = False, 
        - debug: bool =False

        Returns:
        --------
        - fig_avar: plotly.Figure object: Interactive plot of magnitudes and rescaling factors versus log10(time)
                                            in the case of "variable a" fitting
        - fig_a0: plotly.Figure object: Interactive plot of magnitudes and rescaling factors versus log10(time)
                                            in the case of "a0" fitting
        - filterforrescaling: str: The filter used for rescaling (by default, the most numerous, otherwise the customized one).
        - nocolorevolutionlist: list: Filters that show no colour evolution according to the "variable a" fitting.
        - colorevolutionlist: list: Filters that show no colour evolution according to the "variable a" fitting.
        - nocolorevolutionlista0: list: Filters that show no colour evolution according to the "a=0" fitting.
        - colorevolutionlista0: list: Filters that show no colour evolution according to the "a=0" fitting.
        - light: pd.DataFrame: Contains magnitude information.
        - resc_slopes_df: pd.DataFrame: Information on the rescaling factors fitting both in the cases of "variable a" and "a=0".
        - rescale_df: pd.DataFrame: : Contains information of the rescaling factors

        Raises:
        -------
        - None

        """
        
        save_in_folder = None
        if save:
            save_in_folder = self.main_dir + 'colorevol/'
            if not os.path.exists(self.main_dir+save_in_folder):
                os.mkdir(self.main_dir+save_in_folder)

        self.output_colorevol = _colorevolGRB(
                                            self.name, 
                                            self.df, 
                                            chosenfilter, 
                                            print_status, 
                                            return_rescaledf,
                                            save_in_folder, 
                                            debug
                                            )
        return self.output_colorevol


    def rescaleGRB(
        self, 
        remove_duplicate = False,
        save: bool = False
    ):
        """
        Function to rescale the GRB after colour evolution analysis has been performed.
        Rescaling of the filters is applied in the cases only where there is no colour evolution.

        Parameters:
        -----------
        - self: The Lightcurve object should be initialised and colorevolGRB() must be performed to be able to call rescaleGRB().
        - save_in_folder: Path to store the rescaled magnitude file.
        - remove_duplicate: Remove multiple data points at coincident time, by default False.

        Returns:
        --------
        - figunresc: plotly.Figure object: Interactive plot of magnitude lightcurve before rescaling.
        - figresc: plotly.Figure object: Interactive plot of magnitude lightcurve after rescaling.
        - resc_mag_df: pd.DataFrame: DataFrame containing the rescaled magnitudes.

        Raises:
        -------
        - ValueError: If no filters to rescale, i.e. all filters show colour evolution

        """

        save_in_folder = None
        if save:
            save_in_folder = self.main_dir + 'colorevol/'
            if not os.path.exists(self.main_dir+save_in_folder):
                os.mkdir(self.main_dir+save_in_folder)

        return _rescaleGRB(
                        grb = self.name, 
                        output_colorevolGRB = self.output_colorevol, 
                        remove_duplicate = remove_duplicate,
                        save_in_folder = save_in_folder
                        )


major, *__ = sys.version_info # this command checks the Python version installed locally
readfile_kwargs = {"encoding": "utf-8"} if major >= 3 else {} # this option specifies the enconding of imported files in Python
                                                              # the encoding is utf-8 for Python versions superior to 3.
                                                              # otherwise it is left free to the code

def _readfile(path): 
    """
    Function for basic importation of text files.

    """
    with open(path, **readfile_kwargs) as fp:
        contents = fp.read()
    return contents


# re.compile(): compile the regular expression specified by parenthesis to make it match
version_regex = re.compile('__version__ = "(.*?)"') #
contents = _readfile(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__init__.py"
    )
) # this command reads __init__.py that gives the basic functions for the package, namely get_dir, set_dir
__version__ = version_regex.findall(contents)[0]

__directory__ = get_dir()