# standard libs
import os
import re
import sys
from functools import reduce

# third party libs
import numpy as np
import pandas as pd
import lmfit as lf
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
import plotly.express as px
#from matplotlib.figure import Figure

# custom modules
from grblc.util import get_dir
from . import io


class lightcurve:
    _name_placeholder = "unknown grb"
    _flux_fixed_inplace = False


    def __init__(
        self,
        path: str = None,
        #xdata: np.float64 = None,
        #ydata: np.float64 = None,
        #xerr: np.float64 = None,
        #yerr: np.float64 = None,
        #band: str = None,
        appx_bands: str = False,
        name: str = None,
    ):
        """The main module for fitting lightcurves.

        .. warning::
            Data stored in :py:class:`lightcurve` objects are always in logarithmic
            space; the parameter ``data_space`` is only used to convert data to log space
            if it is not already in such. If your data is in linear space [i.e., your
            time data is sec, and not $log$(sec)], then you should set ``data_space``
            to ``lin``.


        Parameters
        ----------
        path : str, optional
            Name of file containing light curve data, by default None
        xdata : array_like, optional
            X values, length (n,), by default None
        ydata : array_like, optional
            Y values, by default None
        xerr : array_like, optional
            X error, by default None
        yerr : array_like, optional
            Y error, by default None
        data_space : str, {log, lin}, optional
            Whether the data inputted is in log or linear space, by default 'log'
        name : str, optional
            Name of the GRB, by default :py:class:`Model` name, or ``unknown grb`` if not
            provided.
        """
        #assert bool(path) ^ (
        #    xdata is not None and ydata is not None
        #), "Either provide a path or xdata, ydata."

        if name:
            self.name = name
        else:
            self.name = self._name_placeholder

        if isinstance(path, str):
            self.path = path
            self.set_data(path, appx_bands=appx_bands, data_space='log')
        #else:
        #    self.path = reduce(
        #        os.path.join,
        #        [
        #            get_dir(),
        #            "lightcurves",
        #            "{}_mag.txt".format(self.name.replace(" ", "_").replace(".", "p")),
        #        ],
        #    )
        #    self.set_data(xdata, ydata, xerr, yerr, band, appx_bands=appx_bands)


    def set_data(self, path: str, appx_bands=False, data_space='log'):
        """
            Reads in data from a file. The data must be in the correct format.
            See the :py:meth:`io.read_data` for more information.

            Set the `xdata` and `ydata`, and optionally `xerr` and `yerr` of the lightcurve.

        .. warning::
            Data stored in :py:class:`lightcurve` objects are always in logarithmic
            space; the parameter ``data_space`` is only used to convert data to log space
            if it is not already in such. If your data is in linear space [i.e., your
            time data is sec, and not log(sec)], then you should set ``data_space``
            to ``lin``.

        Parameters
        ----------
        xdata : array_like
            X data
        ydata : array_like
            Y data
        xerr : array_like, optional
            X error, by default None
        yerr : array_like, optional
            Y error, by default None
        data_space : str, {log, lin}, optional
            Whether the data inputted is in logarithmic or linear space, by default 'log'.
        """

        df = io.read_data(path, data_space=data_space)

        df = df[df['mag_err'] != 0]
        assert len(df)!=0, "Only limiting magnitudes present."

        def convert_data(data):

            for i, band in enumerate(data):
                if band.lower() in ['clear', 'unfiltered', 'lum']:
                    band == band.lower()

            if appx_bands:
                for i, band in enumerate(data):
                    if band.upper()=="u'":
                        data[i]="u"
                    if band.upper()=="g'":
                        data[i]="g"            
                    if band.upper()=="r'":
                        data[i]="r"
                    if band.upper()=="i'":
                        data[i]="i"            
                    if band.upper()=="z'":
                        data[i]="z"            
                    if band.upper()=="BJ":
                        data[i]="B"            
                    if band.upper()=="VJ":
                        data[i]="V"
                    if band.upper()=="UJ":
                        data[i]="U"            
                    if band.upper()=="RM":
                        data[i]="R"             
                    if band.upper()=="BM":
                        data[i]="B"
                    if band.upper()=="UM":
                        data[i]="U"
                    if band.upper()=="JS":
                        data[i]="J"            
                    if band.upper()=="KS":
                        data[i]="K"    
                    if band.upper()=="K'":
                        data[i]="K" 
                    if band.upper()=="KP":
                        data[i]="K" 

                bands = data
            else:
                bands = data

            return bands
        
        
        self.xdata = df["time_sec"].to_numpy()
        self.ydata = df["mag"].to_numpy()
        self.yerr = df["mag_err"].to_numpy()
        self.band = df["band"] = convert_data(df["band"].to_list())
        self.system = df["system"].to_list()
        self.telescope = df["telescope"].to_list()
        self.extcorr = df["extcorr"].to_list()
        self.source = df["source"].to_list()
        self.df = df


    '''def show_data(self, save=False, fig_kwargs={}, save_kwargs={}): # Should masking be included for the rest of the analysis?
        """
            Plots the lightcurve data. If no fit has been ran, :py:meth:`lightcurve.show` will call
            this function.

            .. note:: This doesn't plot any fit results. Use :py:meth:`lightcurve.show_fit` to do so.

            Example:

            .. jupyter-execute::

                import numpy as np
                import grblc

                model = grblc.Model.W07(vary_t=False)
                xdata = np.linspace(0, 10, 15)
                yerr = np.random.normal(0, 0.5, len(xdata))
                ydata = model(xdata, 5, -12, 1.5, 0) + yerr
                lc = grblc.lightcurve(xdata=xdata, ydata=ydata, yerr=yerr, model=model)
                lc.show_data()


        Parameters
        ----------
        fig_kwargs : dict, optional
            Arguments to pass to ``plt.figure()``, by default {}.
        """

        fig_dict = dict(
            figsize=[
                plt.rcParams["figure.figsize"][0],
                plt.rcParams["figure.figsize"][0],
            ]
        )
        if bool(fig_kwargs):
            fig_dict.update(fig_kwargs)
        plot_fig = plt.figure(**fig_dict)
        ax = plot_fig.add_subplot(1, 1, 1)

        xmin, xmax, ymin, ymax = -np.inf, +np.inf, np.inf, +np.inf
        logt = self.orig_xdata
        mag = self.orig_ydata
        logterr = self.orig_xerr
        magerr = self.orig_yerr

        mask = (logt >= xmin) & (logt <= xmax) & (mag >= ymin) & (mag <= ymax)

        # plot all data points inside xmin and xmax in black
        ax.errorbar(
            logt[mask],
            mag[mask],
            xerr=logterr[mask] if logterr is not None else logterr,
            yerr=magerr[mask] if magerr is not None else magerr,
            color="k",
            fmt=".",
            ms=10,
            zorder=0,
        )

        ax_xlim = ax.get_xlim()
        ax_ylim = ax.get_ylim()

        # plot all data points outside of xmin and xmax in grey
        if sum(~mask) > 0:
            ax.errorbar(
                logt[~mask],
                mag[~mask],
                xerr=logterr[~mask] if logterr is not None else logterr,
                yerr=magerr[~mask] if magerr is not None else magerr,
                color="grey",
                fmt=".",
                ms=10,
                alpha=0.2,
                zorder=0,
            )

        ax.set_xlim(ax_xlim)
        ax.set_ylim(ax_ylim)
        ax.set_xlabel("log10 Time (sec)")
        ax.set_ylabel("Magnitudes")
        ax.set_title(self.name)

        plt.show()'''
      
    def displayGRB(self, save_static=False, save_static_type='.png', save_interactive=False, save_in_folder='plots/'):
        #DOES NOT INCLUDE LIMITING MAGS. FIX THIS!

        '''
        For an interactive plot
        '''

        fig = px.scatter(
                    x=self.xdata,
                    y=self.ydata,
                    error_y=self.yerr,
                    color=self.band,
                    hover_data=self.telescope,
                )

        tailpoint_list = []
        for t,m,e in zip(self.xdata,self.ydata,self.yerr):
            if e == 0:
                tailpoint_list.append((t, m))

        headpoint_list = [(i, j+1) for (i, j) in tailpoint_list]

        #make a list of go.layout.Annotation() for each pair of arrow head and tail
        arrows = []
        for head, tail in zip(headpoint_list, tailpoint_list):
            arrows.append(dict(
                x= head[0], #x position of arrowhead
                y= head[1], #y position of arrowhead
                showarrow=True,
                xref = "x", #reference axis of arrow head coordinate_x
                yref = "y",#reference axis of arrow head coordinate_y
                arrowcolor="gray", #color of arrow
                arrowsize = 1.5, #size of arrow head
                arrowwidth = 2, #width of arrow line
                ax = tail[0], #arrow tail coordinate_x
                ay = tail[1], #arrow tail coordinate_y
                axref= "x", #reference axis of arrow tail coordinate_x
                ayref= "y", #reference axis of arrow tail coordinate_y
                arrowhead=3, #annotation arrow head style, from 0 to 8
                ))

        #update_layout with annotations
        fig.update_layout(annotations=arrows)

        font_dict=dict(family='arial',
                    size=18,
                    color='black'
                    )

        fig['layout']['yaxis']['autorange'] = 'reversed'
        fig.update_yaxes(title_text="<b>Magnitude<b>",
                        title_font_color='black',
                        title_font_size=18,
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
                        title_font_size=18,
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
                        title_font_size=25,
                        font=font_dict,
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
  
  
    def rescaleGRB(self, rescale_band='numerous', print_status=True, save_plot=False, save_df=False, save_in_folder='rescale/'):
        """
        This monstrosity performs the color evolution analysis.
        """

        def _overlap(start1, end1, start2, end2):
            #how much does the range (start1, end1) overlap with (start2, end2)
            return max(max((end2-start1), 0) - max((end2-end1), 0) - max((start2-start1), 0), 0)
        

        def wmom(y, yerr, inputmean=None, calcerr=False, sdev=False):
            # https://mail.python.org/pipermail/numpy-discussion/2010-September/052651.html
            """
            NAME:
            wmom()
            
            PURPOSE:
            Calculate the weighted mean, error, and optionally standard deviation of
            an input array.  By default error is calculated assuming the weights are
            1/err^2, but if you send calcerr=True this assumption is dropped and the
            error is determined from the weighted scatter.

            CALLING SEQUENCE:
            wmean,werr = wmom(arr, weights, inputmean=None, calcerr=False, sdev=False)
            
            INPUTS:
            arr: A numpy array or a sequence that can be converted.
            weights: A set of weights for each elements in array.
            OPTIONAL INPUTS:
            inputmean: 
                An input mean value, around which them mean is calculated.
            calcerr=False: 
                Calculate the weighted error.  By default the error is calculated as
                1/sqrt( weights.sum() ).  If calcerr=True it is calculated as sqrt(
                (w**2 * (arr-mean)**2).sum() )/weights.sum()
            sdev=False: 
                If True, also return the weighted standard deviation as a third
                element in the tuple.

            OUTPUTS:
            wmean, werr: A tuple of the weighted mean and error. If sdev=True the
                tuple will also contain sdev: wmean,werr,wsdev

            REVISION HISTORY:
            Converted from IDL: 2006-10-23. Erin Sheldon, NYU
            Modified for our code: 2023-06-30. RFMM
            """
            
            weights = 1/yerr**2
        
            wtot = weights.sum()
                
            # user has input a mean value
            if inputmean is None:
                wmean = ( weights*y).sum()/wtot
            else:
                wmean=float(inputmean)

            # how should error be calculated?
            if calcerr:
                werr2 = ( weights**2 * (y-wmean)**2 ).sum()
                werr = np.sqrt( werr2 )/wtot
            else:
                werr = 1.0/np.sqrt(wtot)

            # should output include the weighted standard deviation?
            if sdev:
                wvar = (weights*(y-wmean)**2 ).sum()/wtot
                wsdev = np.sqrt(wvar)
                return wmean, werr, wsdev
            else:
                return wmean, werr


        light = self.df
        light_x = self.xdata
        light_y = self.ydata
        light_yerr = self.yerr
        light_color = self.band

        assert len(light)>1, "Has only one data point."

        assert rescale_band == 'numerous' or rescale_band in light_color, "Rescaling band provided is not present in data!"

        occur = light['band'].value_counts()
        
        # Identifying the most numerous filter in the GRB 
        if rescale_band=='numerous':
            rescale_filter = occur.index[0]
            rescale_filter_occur = occur[0]
        else:
            rescale_filter = rescale_band
            rescale_filter_occur = occur[rescale_band]

        if print_status:
            print(self.name)
            print('-------')
            print(occur, 'The most numerous filter of this GRB: ',rescale_filter,', with', rescale_filter_occur, 'occurrences.\n'+
                'The most numerous will be considered for rescaling')
        
        scalingfactorslist = [[rescale_filter, rescale_filter_occur, [[0,0,0]]]] ## since the most common filter is not scaled
        
        rescale_light=light.loc[(light['band'] == rescale_filter)]
        rescale_x=rescale_light['time_sec'].values
        rescale_y=rescale_light['mag'].values  
        rescale_yerr=rescale_light['mag_err'].values
        
        for j in range(1, len(occur)):
            scalingfactorslist.append([occur.index[j],occur[j],[]])
        
        evolutionrescalingfactor=[]
        
        for j in range(1,len(occur)):
            
            sublight=light.loc[(light['band'] == occur.index[j])]
            sub_x=sublight['time_sec'].values
            sub_y=sublight['mag'].values
            sub_yerr=sublight['mag_err'].values
            
            timediff = [[p1,p2] for p1 in range(len(rescale_x)) for p2 in range(len(sub_x))
                        if np.abs(rescale_x[p1]-sub_x[p2])<=((rescale_x[p1])*0.025)]

            if len(timediff)!=0:
                for ll in timediff:
                    sf2=[sub_x[ll[1]],
                        rescale_y[ll[0]]-sub_y[ll[1]],
                        np.abs(rescale_x[ll[0]]-sub_x[ll[1]]),
                        np.sqrt(rescale_yerr[ll[0]]**2+sub_yerr[ll[1]]**2)]
                    scalingfactorslist[j][2].append(sf2)

        for fl in scalingfactorslist:

            times=set(el[0] for el in fl[2])
            
            for tt in times:
                suppllist=[fl[2][x] for x in range(len(fl[2])) if fl[2][x][0]==tt]
                suppllistdist=[fl[2][x][2] for x in range(len(fl[2])) if fl[2][x][0]==tt]

                mindistpos=suppllistdist.index(min(suppllistdist))

                evolutionrescalingfactor.append([fl[0],fl[1],suppllist[mindistpos]])    
                
        finalevolutionlist=evolutionrescalingfactor 
        finalevolutionlist=sorted(finalevolutionlist, key=lambda finalevolutionlist: finalevolutionlist[2][0])
      
        filt=[jj[0] for jj in finalevolutionlist if jj[0]!=rescale_filter]
        filtoccur=[jj[1] for jj in finalevolutionlist if jj[0]!=rescale_filter]
        resctime=[jj[2][0] for jj in finalevolutionlist if jj[0]!=rescale_filter]
        rescfact=[jj[2][1] for jj in finalevolutionlist if jj[0]!=rescale_filter]
        rescfacterr=[jj[2][3] for jj in finalevolutionlist if jj[0]!=rescale_filter]
        rescfactweights=[(1/jj[2][3]) for jj in finalevolutionlist if jj[0]!=rescale_filter]
        # lmfit weights as 1/error
        
        rescale_df=pd.DataFrame(list(zip(filt,filtoccur,resctime,rescfact,
                                                    rescfacterr,rescfactweights)),columns=['band','occur_band','time_sec','rescale_fact','rescale_fact_err','rescale_fact_weights'])

        x_all = rescale_df['time_sec']
        y_all = rescale_df['rescale_fact']
        yerr_all = rescale_df['rescale_fact_err']
        filters = [*set(rescale_df['band'].values)]
        rescale_df['plot_color'] = ""

        # Set the color map to match the number of filter
        cmap = plt.get_cmap('gist_ncar')
        cNorm  = colors.Normalize(vmin=0, vmax=len(filters))
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cmap)

        # Plot each filter
        fig = plt.figure()

        for i, band in enumerate(filters):
            colour = scalarMap.to_rgba(i)
            index = rescale_df['band'] == band
            plt.scatter(x_all[index], y_all[index],
                        s=15, 
                        color=colour)
            plt.errorbar(x_all[index], y_all[index], yerr_all[index],
                        fmt='o',
                        barsabove=True,
                        ls='',
                        color=colour
                        )
            for j in rescale_df[index].index:
                rescale_df.at[j,"plot_color"] = colour

        rescale_slopes_df = pd.DataFrame()
        rescale_slopes_df.index = filters
        rescale_slopes_df['slope'] = ""
        rescale_slopes_df['slope_err'] = ""
        rescale_slopes_df['intercept'] = ""
        rescale_slopes_df['inter_err'] = ""
        rescale_slopes_df['acceptance'] = ""
        rescale_slopes_df['red_chi2'] = ""
        rescale_slopes_df['comment'] = ""
        rescale_slopes_df['plot_color'] = ""

        for band in rescale_slopes_df.index:
            ind = rescale_df.index[rescale_df['band'] == band][0]
            rescale_slopes_df.loc[band]['plot_color'] = rescale_df.loc[ind]["plot_color"]
            rescale_band_df = rescale_df[rescale_df['band'] == band]

            x = rescale_band_df['time_sec']
            y = rescale_band_df['rescale_fact']
            yerr = rescale_band_df['rescale_fact_err']
            weights = rescale_band_df['rescale_fact_weights']
            
            ## lmfit linear

            if len(x) >= 3:
                linear_model = lf.models.LinearModel(prefix='line_')
                linear_params = linear_model.make_params()
                
                linear_params['line_slope'].set(value=-1.0)
                linear_params['line_intercept'].set(value=np.max(y))

                linear_fit = linear_model.fit(y, params=linear_params, x=x, weights=weights)
                
                rescale_slopes_df.loc[band]['mean'] = wmom(y)[0]
                rescale_slopes_df.loc[band]['mean_err'] = wmom(y)[1]
                rescale_slopes_df.loc[band]['slope'] = linear_fit.params['line_slope'].value
                rescale_slopes_df.loc[band]['slope_err'] = linear_fit.params['line_slope'].stderr
                rescale_slopes_df.loc[band]['intercept'] = linear_fit.params['line_intercept'].value
                rescale_slopes_df.loc[band]['inter_err'] = linear_fit.params['line_intercept'].stderr
                rescale_slopes_df.loc[band]['acceptance'] = np.abs(rescale_slopes_df.loc[band]['slope_err']/rescale_slopes_df.loc[band]['slope'])
                rescale_slopes_df.loc[band]['red_chi2'] = linear_fit.redchi
                
            else: # not enough data points
                rescale_slopes_df.loc[band]['mean'] = wmom(y)[0]
                rescale_slopes_df.loc[band]['mean_err'] = wmom(y)[1]
                rescale_slopes_df.loc[band]['slope'] = np.nan
                rescale_slopes_df.loc[band]['slope_err'] = np.nan
                rescale_slopes_df.loc[band]['intercept'] = np.nan
                rescale_slopes_df.loc[band]['inter_err'] = np.nan
                rescale_slopes_df.loc[band]['acceptance'] = np.nan
                rescale_slopes_df.loc[band]['comment'] = "insufficient data"
                rescale_slopes_df.loc[band]['red_chi2'] = 'insufficient data'
                
            if rescale_slopes_df.loc[band]['slope'] != np.nan:
                #if rescale_slopes_df.loc[band]['acceptance'] < 10000: #put ad-hoc to have all the plots

                y_fit = rescale_slopes_df.loc[band]['slope'] * x + rescale_slopes_df.loc[band]['intercept']

                plt.plot(x, y_fit, 
                        color=rescale_slopes_df.loc[band]["plot_color"])

                if np.abs(rescale_slopes_df.loc[band]['slope']) < 0.1:
                    rescale_slopes_df.loc[band]['comment'] = "no color evolution"
                elif rescale_slopes_df.loc[band]['slope']-(3*rescale_slopes_df.loc[band]['slope_err'])<=0<=rescale_slopes_df.loc[band]['slope']+(3*rescale_slopes_df.loc[band]['slope_err']):
                    rescale_slopes_df.loc[band]['comment'] = "no color evolution"
                else:    
                    rescale_slopes_df.loc[band]['comment'] = "slope >= 0.1"

            else:
                rescale_slopes_df.loc[band]['comment'] = "slope=nan"  

        for band in rescale_slopes_df.index:
            ind = rescale_df.index[rescale_df['band'] == band][0]
            color = rescale_df.loc[ind]["plot_color"]
            plt.scatter(x=[], y=[], 
                        color=color, 
                        label=band+": "+ str(rescale_slopes_df.loc[band]["slope"]) + r'$\pm$' + str(rescale_slopes_df.loc[band]["slope_err"])
                        )
    
        plt.rcParams['legend.title_fontsize'] = 'xx-large'
        plt.xlabel('Log time (s)',fontsize=22)
        plt.ylabel('Rescaling factor with respect to '+rescale_filter+' (mag)',fontsize=22)
        plt.rcParams['figure.figsize'] = [15, 10]
        plt.xticks(fontsize=22)
        plt.yticks(fontsize=22)
        plt.title("GRB "+self.name, fontsize=22)
        plt.legend(title='Band & slope', bbox_to_anchor=(1.015, 1.015), loc='upper left', fontsize='xx-large')    
        plt.tight_layout()

        if save_plot:
            plt.savefig(os.path.join(save_in_folder+'/'+str(self.name)+'_colorevol.pdf'), dpi=300)


        rescale_df.drop(labels='plot_color', axis=1, inplace=True)
        rescale_slopes_df.drop(labels='plot_color', axis=1, inplace=True)

        if print_status:

            print("Individual point rescaling:")
            print(rescale_df)

            print("\nSlopes of rescale factors for each filter:")
            print(rescale_slopes_df)
             
            compatibilitylist=[]
    
            for band in rescale_slopes_df.index:
                if rescale_slopes_df.loc[band]['slope']!=0 and rescale_slopes_df.loc[band]['slope_err']!=0:
                    compatibilitylist.append([band,[rescale_slopes_df.loc[band]['slope']-(3*rescale_slopes_df.loc[band]['slope_err']),
                                            rescale_slopes_df.loc[band]['slope']+(3*rescale_slopes_df.loc[band]['slope_err'])]])

            compzerolist=[]
            nocompzerolist=[]
            for l in compatibilitylist:
                if l[1][0]<=0<=l[1][1] or np.abs((l[1][0]+l[1][1])/2)<0.10:
                        compzerolist.append(l[0])
                else:
                    nocompzerolist.append(l[0])

            if len(compzerolist)==0:
                print('No filters compatible with zero in 3sigma or with |slope|<0.1')
                
            else:
                print('Filters compatible with zero in 3sigma: ',*compzerolist)
            
            if len(nocompzerolist)==0:
                print('No filters with |slope|>0.1 or compatible with zero only in >3sigma')
                
            else:
                print('Filters not compatible with zero in 3sigma or with |slope|>0.1: ',*nocompzerolist)    

            print('\n')
            print('No color evolution: ',*compzerolist,' ; Color evolution: ',*nocompzerolist)        

            
            string=""
            for band in rescale_slopes_df.index:
                string=string+band+":"+str(round(rescale_slopes_df.loc[band]['slope'],3))+"+/-"+str(round(rescale_slopes_df.loc[band]['slope_err'],3))+"; "
                
            print(string)

        # RESCALING PART OF THE LC

        #averagedrescalingfactor=[]
        #for c in range(len(scalingfactorslist)):
                                              #[c][2][x][3] 3 for the rescaling factor error
        #    rescfactfilter=[scalingfactorslist[c][2][x][1] for x in range(len(scalingfactorslist[c][2]))]
        #    if np.isnan(np.mean(rescfactfilter))==False:
        #        averagedrescalingfactor.append([scalingfactorslist[c][0],scalingfactorslist[c][1],np.mean(rescfactfilter)])

        #    if np.isnan(np.mean(rescfactfilter))==True:
        #        averagedrescalingfactor.append([scalingfactorslist[c][0],scalingfactorslist[c][1],0]) 
        
        # The light frame is the one that will be rescaled
        
        for pp in range(len(light)):
            start2=light_y[pp]-light_yerr[pp]
            end2=light_y[pp]+light_yerr[pp]
            supportlistov=[]
            supportlistdist=[]
         
            for mean, mean_err in zip(rescale_df['mean'], rescale_df['mean_err']):
                if light_color[pp] == rescale_df['band']:
                    for nn in [x for x in range(len(light)) if (x != pp) & (light_color[x]==rescale_filter)]:
                        start1=light_y[nn]-light_yerr[nn] 
                        end1=light_y[nn]+light_yerr[nn] 
                        dist=np.abs((light_x[nn])-(light_x[pp]))/(light_x[nn])
                        supportlistov.append(_overlap(start1, end1, start2, end2))
                        supportlistdist.append(dist)

                    if any((supportlistov[i] == 0) & (supportlistdist[i] <= 0.025) for i in range(len(supportlistov))):
                        light_y[pp]=light_y[pp]+mean
                        light_yerr[pp]=np.sqrt(light_yerr[pp]**2 + mean_err**2)
                        #print('rescaling is evaluated with ',ff[2])
                    else:
                        pass
                        #print('rescaling is NOT evaluated')

        # change to matplotlib

        figresc = px.scatter(
                x=light_x,
                y=light_y,
                error_y=light_yerr,
                color=light_color,
                hover_data=['telescope', 'source'],
                )

        font_dict=dict(family='arial',
                    size=18,
                    color='black'
                    )

        figresc['layout']['yaxis']['autorange'] = 'reversed'
        figresc.update_yaxes(title_text="<b>Magnitude<b>",
                        title_font_color='black',
                        title_font_size=18,
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

        figresc.update_xaxes(title_text="<b>log10 Time (s)<b>",
                        title_font_color='black',
                        title_font_size=18,
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

        figresc.update_layout(title="GRB " + self.name + " rescaled",
                        title_font_size=25,
                        font=font_dict,
                        plot_bgcolor='white',  
                        width=960,
                        height=540,
                        margin=dict(l=40,r=40,t=50,b=40)
                        )
        
        if save_plot:
            plt.savefig(os.path.join(save_in_folder+'/'+str(self.name)+'_colorevol.pdf'), dpi=300)
        if save_df:
            light.to_csv(os.path.join(save_in_folder+'/'+str(self.name)+'_colorevol.txt'), sep='\t')
 
        return fig, rescale_df, rescale_slopes_df, figresc, light



major, *__ = sys.version_info
readfile_kwargs = {"encoding": "utf-8"} if major >= 3 else {}


def _readfile(path):
    with open(path, **readfile_kwargs) as fp:
        contents = fp.read()
    return contents


version_regex = re.compile('__version__ = "(.*?)"')
contents = _readfile(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__init__.py"
    )
)
__version__ = version_regex.findall(contents)[0]

__directory__ = get_dir()
