import ROOT as rt
import os, sys, optparse
from collections import OrderedDict
import math

#----------------------------------------------------------------------------
## round x to n significant figures
def round_to_n(x,n):
    result=x
    if x!=0:
       x=round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))
    return x

#____________________________________________________________________________
def get_mean_and_sigma(theHist, wmin=0.2, wmax=1.8, step=0.001, epsilon=0.007):

    ## rms, signal peak position

    mu = 1
    sig = 0
    sig_eff = 0

    #print theHist.Integral()
    if theHist.Integral() > 0:
        x0 = theHist.GetXaxis().GetBinCenter(theHist.GetMaximumBin())
        d  = theHist.GetRMS()

        # now perform gaussian fit in [x_max_sigm, x_max_sigp]
        f = rt.TF1('gausfit', 'gaus', wmin, wmax)

        s = 1.0
        theHist.Fit('gausfit', 'Q', '', x0 - s*d, x0 + s*d)

        mu  = f.GetParameter(1)
        #mu  = x0
        sig = f.GetParameter(2)

        #print mu, sig

        point = wmin
        weight = 0.
        points = [] #vector<pair<double,double> > 
        thesum = theHist.Integral()
        for i in range(theHist.GetNbinsX()):
          weight += theHist.GetBinContent(i)
          if weight > epsilon:
            points.append( [theHist.GetBinCenter(i),weight/thesum] )
        low = wmin
        high = wmax

        #print points

        width = wmax-wmin
        for i in range(len(points)):
          for j in range(i,len(points)):
            wy = points[j][1] - points[i][1]
            if abs(wy-0.683) < epsilon:

              wx = points[j][0] - points[i][0]
              if wx < width:
                low = points[i][0]
                high = points[j][0]
                width=wx

        sig_eff = 0.5*(high-low)

    #print mu,sig, sig_eff
    return mu,sig, sig_eff

#_________________________________________________________________________________

## THIS FUNCTION REMOVES THE SPURIOUS + SIGN AND CONVERTS THE LIST OF STRINGS INTO A STRING
def clean_dump(dump):
    last_line = dump[-1]
    last_char_index = last_line.rfind("+")
    new_string = last_line[:last_char_index] + " " + last_line[last_char_index+1:]
    #print new_string
    dump[-1] = new_string
    dump.append('  }')

    #print dump
    chunk_text='\n'
    chunk_text=chunk_text.join(dump)

    #print chunk_text
    return chunk_text

#_________________________________________________________________________________

## THIS FUNCTION REMOVES THE SPURIOUS + SIGN AND CONVERTS THE LIST OF STRINGS INTO A STRING
def clean_dump_jec(dump):

    #print dump
    chunk_text='\n'
    chunk_text=chunk_text.join(dump)

    #print chunk_text
    return chunk_text



#_________________________________________________________________________________

## this function replaces content between the two control strings
def replaced(base, content, starting, ending):

    partitioned_string = base.partition(starting)
    before=partitioned_string[0]
    after=partitioned_string[2]
    partitioned_after=after.partition(ending)
    after=partitioned_after[2]

    #final=before+'\n'+starting+'\n'+content+'\n'+ending+'\n'+after
    final=before+content+after
    return final 

#_________________________________________________________________________________

## this function computes efficiencies ratio scale factors and dumps them into card

def dump_efficiencies_ratio(collection, quality, lines_eff, id2D_f, id2D_d, content):

    lines_eff.append('  ### {} {} ID \n'.format(collection,quality))
    lines_eff.append('  set EfficiencyFormula {\n')

    ### calculate residual efficiency
    for ybin in range(0,id2D_f.GetNbinsY()): ## eta
        isetaOF = False
        #print id2D_f.GetBinContent(ybin+1), id2D_d.GetBinContent(ybin+1)

        if id2D_f.GetYaxis().GetBinWidth(ybin+1) == 0: continue
        etalow = id2D_f.GetYaxis().GetBinLowEdge(ybin+1)
        etahigh = id2D_f.GetYaxis().GetBinUpEdge(ybin+1)
        if etahigh > 10: isetaOF = True

        pt_first = id2D_f.GetXaxis().GetBinLowEdge(1)
        string = "   (abs(eta) > "+str(etalow)+" && abs(eta) <= "+str(etahigh)+") * (pt <= "+str(pt_first)+") * (0.0) +"
        #print string
        lines_eff.append(string)
        
        for xbin in range (0,id2D_f.GetNbinsX()): ##pt
            isptOF = False

            #print id2D_f.GetBinContent(xbin+1,ybin+1), id2D_d.GetBinContent(xbin+1,ybin+1)

            if id2D_f.GetXaxis().GetBinWidth(xbin+1) == 0: continue
            ptlow = id2D_f.GetXaxis().GetBinLowEdge(xbin+1)
            pthigh = id2D_f.GetXaxis().GetBinUpEdge(xbin+1)
            if pthigh > 9e4: isptOF = True

            '''
            ratio = id2D_f.GetBinContent(xbin+1,ybin+1)
            if useIso: 
                delpheseff = iso2D_d.GetBinContent(xbin+1,ybin+1)
                if delpheseff > 0: 
                    ratio = ratio * iso2D_f.GetBinContent(xbin+1,ybin+1)/delpheseff
                else: ratio = ratio * iso2D_f.GetBinContent(xbin+1,ybin+1)
            '''
            

            eff_d = id2D_d.GetBinContent(xbin+1,ybin+1)
            eff_f = id2D_f.GetBinContent(xbin+1,ybin+1)
            
            #print etalow, etahigh, ptlow, pthigh, eff_d, eff_f
            
            ratio = -1.0
            
            if eff_f == 0:
                if ptlow > 30.:
                    ratio = 1.
                else:
                    ratio = 0.
            else:
                if eff_d < eff_f:
                    ratio = 1.
                else :
                    ratio = eff_f/eff_d

            if ybin == id2D_f.GetNbinsY()-1:
                ratio = 0.0

            ratio = round_to_n(ratio,2)
            if isptOF:
                if isetaOF: string = "   (abs(eta) > "+str(etalow)+") * (pt > "+str(ptlow)+") * ("+str(ratio)+") +"
                else: string = "   (abs(eta) > "+str(etalow)+" && abs(eta) <= "+str(etahigh)+") * (pt > "+str(ptlow)+") * ("+str(ratio)+") +"
            else:
                if isetaOF: string = "   (abs(eta) > "+str(etalow)+") * (pt > "+str(ptlow)+" && pt <= "+str(pthigh)+") * ("+str(ratio)+") +"
                else: string = "   (abs(eta) > "+str(etalow)+" && abs(eta) <= "+str(etahigh)+") * (pt > "+str(ptlow)+" && pt <= "+str(pthigh)+") * ("+str(ratio)+") +"

            lines_eff.append(string)
            print string

    dump_eff=lines_eff
    dump_eff=clean_dump(dump_eff)

    print dump_eff

    starting_eff = '## DUMMY_' + collection.upper() + '_'+ quality.upper() + 'ID_EFFICIENCY'
    ending_eff = starting_eff.replace('DUMMY','ENDDUMMY')

    print starting_eff
    print ending_eff

    content2=replaced(content, dump_eff, starting_eff, ending_eff)
    return content2

#_________________________________________________________________________________

## this function computes efficiencies scale factors and dumps them into card

def dump_efficiencies(collection, quality, lines_fake, pdgcode, fake2D_f, content):

    ## ex: DUMMY_PHOTONMediumID_EFFICIENCY

    if  collection!= 'btag' and  collection!= 'tautag' :
        lines_fake.append('  {{{}}} {{\n'.format(pdgcode))
    else:
        lines_fake.append('  add EfficiencyFormula {{{}}} {{\n'.format(pdgcode))

    ### calculate residual efficiency
    for ybin in range(0,fake2D_f.GetNbinsY()): ## eta
        isetaOF = False

        if fake2D_f.GetYaxis().GetBinWidth(ybin+1) == 0: continue
        etalow = fake2D_f.GetYaxis().GetBinLowEdge(ybin+1)
        etahigh = fake2D_f.GetYaxis().GetBinUpEdge(ybin+1)
        if etahigh > 10: isetaOF = True

        ## have to set to 0 effciency before first bin:
        pt_first = fake2D_f.GetXaxis().GetBinLowEdge(1)
        pt_first = fake2D_f.GetXaxis().GetBinLowEdge(1)
        string = "          (abs(eta) > "+str(etalow)+" && abs(eta) <= "+str(etahigh)+") * (pt <= "+str(pt_first)+") * (0.0) +"
        #print string
        lines_fake.append(string)
        
        
        for xbin in range (0,fake2D_f.GetNbinsX()): ##pt
            isptOF = False

            if fake2D_f.GetXaxis().GetBinWidth(xbin+1) == 0: continue
            ptlow = fake2D_f.GetXaxis().GetBinLowEdge(xbin+1)
            pthigh = fake2D_f.GetXaxis().GetBinUpEdge(xbin+1)
            if pthigh > 9e4: isptOF = True

            eff_f = fake2D_f.GetBinContent(xbin+1,ybin+1)
            eff_f = round_to_n(eff_f,2)
            if isptOF:
                if isetaOF: string = "          (abs(eta) > "+str(etalow)+") * (pt > "+str(ptlow)+") * ("+str(eff_f)+") +"
                else: string = "          (abs(eta) > "+str(etalow)+" && abs(eta) <= "+str(etahigh)+") * (pt > "+str(ptlow)+") * ("+str(eff_f)+") +"
            else:
                if isetaOF: string = "          (abs(eta) > "+str(etalow)+") * (pt > "+str(ptlow)+" && pt <= "+str(pthigh)+") * ("+str(eff_f)+") +"
                else: string = "         (abs(eta) > "+str(etalow)+" && abs(eta) <= "+str(etahigh)+") * (pt > "+str(ptlow)+" && pt <= "+str(pthigh)+") * ("+str(eff_f)+") +"

            lines_fake.append(string)
            #print string

    dump_fake=lines_fake
    dump_fake=clean_dump(dump_fake)

    print dump_fake

    starting_fake = '## DUMMY_' + collection.upper() + '_'+ quality.upper() + 'ID_DUMP'
    ending_fake = starting_fake.replace('DUMMY','ENDDUMMY')

    print starting_fake
    print ending_fake

    content2=replaced(content, dump_fake, starting_fake, ending_fake)
    return content2


#__________________________________________________________________________________

rt.gROOT.SetBatch(True) ## avoid figures pop out to screen

usage = 'usage: %prog [options]'
parser = optparse.OptionParser(usage)

parser.add_option('-f','--flat',
                  action="store_true",
                  dest='flat',
                  default=False,
                  help='true/false dump flat card for tuning')

parser.add_option('--card-in',
                  dest='card_in',
                  help='path to dummy delphes card [%default]',  
                  default='cards/dummy.tcl',                                                                                                           
                  type='string')

parser.add_option('--card-out',
                  dest='card_out',
                  help='path to output delphes card [%default]',  
                  default='cards/out_card.tcl',                                                                                                           
                  type='string')

parser.add_option('-j','--dump_jec',
                  action="store_true",
                  dest='dump_jec',
                  default=False,
                  help='true/false dump jec_correction')

parser.add_option('--skip_reso',
                  action="store_true",
                  dest='skip_reso',
                  default=False,
                  help='skip dumping scale and resolution')

parser.add_option('--skip_eff',
                  action="store_true",
                  dest='skip_eff',
                  default=False,
                  help='skip dumping efficiencies and fake rates')



#path_delphes='/eos/cms/store/group/upgrade/RTB/ValidationHistos/delphes343pre10_v11_dummy/'
#path_delphes='/eos/cms/store/group/upgrade/RTB/ValidationHistos/delphes343pre11_v12_dummy/'
path_delphes='/eos/cms/store/group/upgrade/RTB/ValidationHistos/delphes343pre11_v13b/'
path_delphes='/eos/cms/store/group/upgrade/RTB/ValidationHistos/delphes343pre11_v14a/'
path_delphes='/eos/cms/store/group/upgrade/RTB/ValidationHistos/delphes343pre11_v14b/'
path_delphes='/eos/cms/store/group/upgrade/RTB/ValidationHistos/delphes343pre12_v14e/'

#path_fullsim='/eos/cms/store/group/upgrade/RTB/ValidationHistos/fullsim_Iter6/'
#path_fullsim='/eos/cms/store/group/upgrade/RTB/ValidationHistos/fullsim_Iter6_JEC/'
path_fullsim='/eos/cms/store/group/upgrade/RTB/ValidationHistos/fullsim_Iter6_JEC/'

elmu_delphes=path_delphes+'/HistosDELPHES_ELMu.root'
gamma_delphes=path_delphes+'/HistosDELPHES_Photon.root'
jets_delphes=path_delphes+'/HistosDELPHES_QCD.root'
btag_delphes=path_delphes+'/HistosDELPHES_BTag.root'
tautag_delphes=path_delphes+'/HistosDELPHES_TauTag.root'


elmu_fullsim=path_fullsim+'/HistosFS_ELMu_113X.root'
gamma_fullsim=path_fullsim+'/HistosFS_Photon_113X.root'
jets_fullsim=path_fullsim+'/HistosFS_QCD_113X.root'
btag_fullsim=path_fullsim+'/HistosFS_BTag_112X.root'
tautag_fullsim=path_fullsim+'/HistosFS_TauTag_112X.root'

object_dict={
              'muon':{
                        'collection':'muon',
                        'fit_range':[0.9,1.1],
                        'scale_quality':'looseIDISO', ## collection used for momentum scale and smearing
                        #'qualities':['loose','medium','tight'], ## (will look for string "DUMMY_MUON_{quality}ID_EFFICIENCY or DUMMY_MUON_{quality}ID_FAKERATE )
                        'qualities':['tight'], ## (will look for string "DUMMY_MUON_{quality}ID_EFFICIENCY or DUMMY_MUON_{quality}ID_FAKERATE )
                        'file_prompt_F':elmu_fullsim,
                        'file_fake_F':jets_fullsim,
                        'file_prompt_D':elmu_delphes,
              },
              
              'electron':{
                        'collection':'electron',
                        'fit_range':[0.9,1.1],
                        'scale_quality':'looseIDISO', ## collection used for momentum scale and smearing
                        'qualities':['loose','medium','tight'], ## here store qualities used to produce efficiencies and fake-rate (dummy for now)
                        'file_prompt_F':elmu_fullsim,
                        'file_fake_F':jets_fullsim,
                        'file_prompt_D':elmu_delphes,

              },

              'photon':{
                        'collection':'photon',
                        'fit_range':[0.9,1.1],
                        'scale_quality':'looseIDISO', ## collection used for momentum scale and smearing
                        'qualities':['loose','medium','tight'], ## here store qualities used to produce efficiencies and fake-rate (dummy for now)
                        'file_prompt_F':gamma_fullsim,
                        'file_fake_F':jets_fullsim,
                        'file_prompt_D':gamma_delphes,
                        
              },

              'jet':{
                        'collection':'jetpuppi',
                        'fit_range':[0.0,2.0],
                        'scale_quality':'tightID', ## collection used for momentum scale and smearing
                        #'scale_quality':'reco', ## collection used for momentum scale and smearing
                        'qualities':['loose','tight'], ## here store qualities used to produce efficiencies and fake-rate (dummy for now)
                        'file_prompt_F':jets_fullsim,
                        'file_prompt_D':jets_delphes,
              },


              'btag':{
                        'collection':'jetpuppi',
                        'fit_range':[-1,-1], ## dummy values for b/tau tagging
                        'scale_quality':'dummy', ## dummy values for b/tau tagging
                        'qualities':['loose','medium','tight'], ## here store qualities used to produce efficiencies
                        'tag_pid':{'btag': 5,
                                   'cMistag': 4,
                                   'lightMistag': 0
                                   }, ## here store mapping between efficiencies labels and PID

                        'file_prompt_F':btag_fullsim,
                        'file_prompt_D':btag_delphes,
              },

              'tautag':{
                        'collection':'tau',
                        'fit_range':[-1,-1], ## dummy values for b/tau tagging
                        'scale_quality':'dummy', ## dummy values for b/tau tagging
                        'qualities':['loose','medium','tight'], ## here store qualities used to produce efficiencies
                        'tag_pid':{'tautag': 15,
                                   'lightMistag': 0,
                                   #'elecMistag': 11,
                                   #'muonMistag': 13
                                   }, ## here store mapping between efficiencies labels and PID

                        'file_prompt_F':tautag_fullsim,
                        ## have to do this because there are no electrons in 11_2 samples
                        'file_fake_F':elmu_fullsim,
                        'file_prompt_D':tautag_delphes,
              },


}


(opt, args) = parser.parse_args()

flat = opt.flat


### dump dummy card content into string
with open(opt.card_in, 'r') as f:
    base = f.read()

content=base

for obj, params in object_dict.items():

    print obj
    #if obj != 'tautag': continue
    #if obj != 'btag': continue
    if obj != 'muon': continue
    #if obj == 'photon': continue
    #if obj != 'electron': continue
    #if obj != 'jet': continue

    #obj['']
    collection=params['collection']
    scale_quality=params['scale_quality']

    starting_scale = '## DUMMY_'+collection.upper()+'_SCALE'
    ending_scale = starting_scale.replace('DUMMY','ENDDUMMY')
    
    starting_smear = '## DUMMY_'+collection.upper()+'_SMEAR'
    ending_smear = starting_smear.replace('DUMMY','ENDDUMMY')

    file_prompt_F=params['file_prompt_F']
    file_prompt_D=params['file_prompt_D']

    fit_range_min=params['fit_range'][0]
    fit_range_max=params['fit_range'][1]

    print file_prompt_F
    print file_prompt_D
    
    inputFile_d = rt.TFile.Open(file_prompt_D)
    inputFile_f = rt.TFile.Open(file_prompt_F)

    ## these dicts contain resolutions to be dumped in tcl format
    mean_and_sigmas_d = OrderedDict()
    mean_and_sigmas_f = OrderedDict()

    hist_names = []

    if not hist_names: 
        keys = inputFile_d.GetListOfKeys()
        hist_names = [x.GetName() for x in keys] 
        hist_names.sort()

    for name in hist_names:
        canv_name = name
        canv = rt.TCanvas(canv_name, canv_name, 900, 600)
        hd = inputFile_d.Get(name)
        hf = inputFile_f.Get(name)
        '''
        try:
            test = hf.Integral()
            if test == 0: continue
        except:
            continue
        '''
        #print name
        
        if obj not in name: continue

        if 'resolution' in name:
            items = name.split('_')
            #print items

            colname = items[0]
            quality = items[1]
            ptmin = items[4]
            ptmax = items[5]
            etamin = items[7].replace('p','.')
            etamax = items[8].replace('p','.')

            if 'Inf' in ptmax:
                ptmax = 14000.
            if 'Inf' in etamax:
                etamax = 5.

            etamin = float(etamin)
            etamax = float(etamax)
            ptmin = float(ptmin)
            ptmax = float(ptmax)


            if quality != scale_quality: continue
            
            #print colname, quality, ptmin, ptmax, etamin, etamax

            ## form input ntuple for mean_and_sigmas dictionary
            ntup_in = (colname, quality, ptmin, ptmax, etamin, etamax)

            mean_and_sigmas_d[ntup_in] = get_mean_and_sigma(hd, wmin=fit_range_min, wmax=fit_range_max, step=0.001, epsilon=0.005)
            mean_and_sigmas_f[ntup_in] = get_mean_and_sigma(hf, wmin=fit_range_min, wmax=fit_range_max, step=0.001, epsilon=0.005)

        ### HERE IS WHERE WE COMPUTE EFFICIENCY RATIOS AND FAKE RATE

    if obj != 'btag' and obj != 'tautag': 
        ## HERE IS WHERE WE COMPUTE THE VALUES AND DUMP THE RESOLUTION IN THE INPUT TCL FILE 

        ntup_list = mean_and_sigmas_f.keys()

        ## order first by collection , then by quality, then by eta min, then by ptmin 
        sorted_ntup_list = sorted(ntup_list, key=lambda v: (v[0], v[1], v[4], v[2]))

        old_coll = ''
        old_quality = ''
        old_etamin = -1
        old_etamax = -1
        old_ptmin = -1
        old_ptmax = -1

        lines_scale = dict()
        lines_reso = dict()

        lines_jec = dict()


        scale = 1.
        for ntup_in in sorted_ntup_list:

            coll    = ntup_in[0]
            quality = ntup_in[1]
            ptmin   = ntup_in[2]
            ptmax   = ntup_in[3]
            etamin  = ntup_in[4]
            etamax  = ntup_in[5]

            if quality != scale_quality:
                continue

            if coll != old_coll:
                old_coll = coll

            if quality != old_quality:

                old_quality = quality
                lines_scale[(coll,quality)] = []
                lines_scale[(coll,quality)].append('  ### {} {} momentum scale'.format(coll, quality))
                lines_scale[(coll,quality)].append('  set ScaleFormula {')

                lines_reso[(coll,quality)] = []
                lines_reso[(coll,quality)].append('  ### {} {} momentum resolution'.format(coll, quality))
                lines_reso[(coll,quality)].append('  set ResolutionFormula {')

                lines_jec[(coll,quality)] = []
                lines_jec[(coll,quality)].append('float jec(float pt, float eta)')
                lines_jec[(coll,quality)].append('{')
                lines_jec[(coll,quality)].append('  float scale = 1.;')

            ## compute values to write in delphes card

            if opt.dump_jec: mu_d = 1
            else: mu_d = mean_and_sigmas_d[ntup_in][0]
            
            mu_f = mean_and_sigmas_f[ntup_in][0]

            ## 1 - is gaussian width and 2 - is effective width
            sigma_d = mean_and_sigmas_d[ntup_in][2]
            if opt.dump_jec: sigma_d = 0.2
            sigma_f = mean_and_sigmas_f[ntup_in][2]

            if opt.dump_jec: sigma0_d = 0.2
            else: sigma0_d = mean_and_sigmas_d[ntup_in][1]
            sigma0_f = mean_and_sigmas_f[ntup_in][1]

            scale_f = 1.
            scale_d = 1.

            if mu_d > 0.:   ## otherwise pick value from previous bin
                scale_d = 1. / mu_d
            if mu_f > 0.:   ## otherwise pick value from previous bin
                scale_f = 1./ mu_f 

            ## delphes resolution when morphed to full sim scale

            #print scale_d, scale_f
            sigmap_d = sigma_d *scale_d
            sigmap_d0 = sigma0_d*scale_d
            
            #print sigma_d, sigma_f

            sigmap_f = sigma_f *scale_f
            sigmap_f0 = sigma0_f*scale_f

            #print sigmap_d, sigmap_f

            sigma_smear = 1.e-06
            sigma_smear0 = 1.e-06
            if sigmap_f**2 > sigmap_d**2: 
                sigma_smear = math.sqrt(sigmap_f**2 - sigmap_d**2)
                #print sigma_smear, sigmap_f, sigmap_d

            if sigmap_f0**2 > sigmap_d0**2: 
                sigma_smear0 = math.sqrt(sigmap_f0**2 - sigmap_d0**2)

            sigma_smear = round_to_n(sigma_smear,3)
            sigma_smear0 = round_to_n(sigma_smear0,3)
            scale = round_to_n(scale,2)

            print ' --- new pt bin ',  ptmin, ptmax, etamin, etamax, '------'
            print ''
            print 'muf: ', round_to_n(mu_f,3), ', mud', round_to_n(mu_d,3)
            print 'sigma_f: ', round_to_n(sigmap_f,3), ', sigma_d',round_to_n(sigmap_d,3)
            print 'sigma_f0: ', round_to_n(sigmap_f0,3), ', sigma_d0',round_to_n(sigmap_d0,3)
            #print 'sigmaeff_f: ', round_to_n(sigma_f,3), ', sigmaeff_d',round_to_n(sigma_d,3)
            #print 'sigmaeff_f0: ', round_to_n(sigma0_f,3), ', sigmaeff_d0',round_to_n(sigma0_d,3)
            print 'sigma_smear0 ', sigma_smear0, ', sigma_smear', sigma_smear
            #print 'sigma_smear', sigma_smear
            print ''

            lines_scale[(coll,quality)].append('   (abs(eta) > {:.1f} && abs(eta) <= {:.1f}) * (pt > {:.1f} && pt <= {:.1f}) * ({:.3f}) +'.format(etamin, etamax, ptmin, ptmax, scale_d))
            lines_reso[(coll,quality)].append('   (abs(eta) > {:.1f} && abs(eta) <= {:.1f}) * (pt > {:.1f} && pt <= {:.1f}) * ({:.2f}) +'.format(etamin, etamax, ptmin, ptmax, sigma_smear))
            
            print (coll,quality)
            lines_jec[(coll,quality)].append('  if (fabs(eta) > {:.1f} && fabs(eta) <= {:.1f} && pt > {:.1f} && pt <= {:.1f}) scale = {:.2f};'.format(etamin, etamax, ptmin, ptmax, scale_f))

        lines_jec[(collection,quality)].append('  return scale;')
        lines_jec[(collection,quality)].append('}')

        dump_scale=lines_scale[(collection,scale_quality)]
        dump_reso=lines_reso[(collection,scale_quality)]

        dump_scale=clean_dump(dump_scale)
        dump_reso=clean_dump(dump_reso)

        if coll == 'jetpuppi' and opt.dump_jec:
            dump_jec=lines_jec[(coll,scale_quality)]
            dump_jec = clean_dump_jec(dump_jec)
            out_jec = open('jec.txt', "w")
            n = out_jec.write(dump_jec)
            out_jec.close()

        print dump_scale    
        print dump_reso

        ## HERE REPLACE CONTENT OF THE CARD BETWEEN CONTROL STRINGS 

        if not flat and not opt.skip_reso:
            ## scale parametrisation
            content=replaced(content, dump_scale, starting_scale, ending_scale)

            ## smear parametrisation  
            content=replaced(content, dump_reso, starting_smear, ending_smear)

    ## ADD HERE VARIOUS EFFICIENCIES AND FAKE RATES

    if not opt.skip_eff:
        for quality in params['qualities']:

            if obj != 'btag' and obj != 'tautag' :

                dumpname='efficiency2D_'+quality+'IDISO'
                if collection == 'jetpuppi':
                    dumpname='efficiency2D_'+quality+'ID'

                name=collection+'_'+dumpname

                print quality, name

                id2D_f = inputFile_f.Get(name).ProjectionXY("id_"+name+"_f")
                id2D_d = inputFile_d.Get(name).ProjectionXY("id_"+name+"_d")

                lines_eff = []
                if not flat:
                    content = dump_efficiencies_ratio(collection, quality, lines_eff, id2D_f, id2D_d, content)


            if obj == 'btag' or obj == 'tautag' :
                for tag, pid in params['tag_pid'].items():
                    print tag, pid

                    dumpname=tag+'Rate_2D_'+quality+'ID'
                    if obj == 'tautag' :
                        dumpname=tag+'Rate_efficiency2D_'+quality+'ID'

                    name=collection+'_'+dumpname

                    print name
                    pdgcode=pid
                    ### extract 2D map from full sim 
                    if pdgcode!=11:
                        eff2D_f = inputFile_f.Get(name)
                    else:
                        file_fake_F=params['file_fake_F']
                        inputFile_fake_f = rt.TFile.Open(file_fake_F)
                        eff2D_f = inputFile_fake_f.Get(name)

                    lines_eff = []

                    print obj, tag+'_'+quality,pdgcode

                    if not flat:
                        content = dump_efficiencies(obj, tag+'_'+quality, lines_eff, pdgcode, eff2D_f, content)


            #if 'file_fake_F' in params: ## exclude jets
            ## dump fake rates here
            if collection=='electron' or collection=='muon' or collection=='photon': ## exclude jets

                file_fake_F=params['file_fake_F']
                fakeFile_f = rt.TFile.Open(file_fake_F)

                pdgcode=-1
                if collection=='electron': pdgcode=11
                elif collection=='muon': pdgcode=13
                elif collection=='photon': pdgcode=22

                ### extract fakerate
                name_fake=collection+'_fakerate2D_'+quality+'IDISO'
                fake2D_f = fakeFile_f.Get(name_fake)

                print name_fake

                lines_fake = []

                if not flat:
                    content = dump_efficiencies(collection, quality, lines_fake, pdgcode, fake2D_f, content)
                else:
                    flat_param='  {{{}}} {{0.0001}}\n'.format(pdgcode)
                    starting_fake = '## DUMMY_' + collection.upper() + '_'+ quality.upper() + 'ID_DUMP'
                    ending_fake = starting_fake.replace('DUMMY','ENDDUMMY')
                    content=replaced(content, flat_param, starting_fake, ending_fake)

## dump new content into new delphes card


out_card = open(opt.card_out, "w")
n = out_card.write(content)
out_card.close()
