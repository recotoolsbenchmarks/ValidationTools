
import ROOT as rt
import os, sys, optparse
from collections import OrderedDict
import math
#____________________________________________________________________________
def get_mean_and_sigma(theHist, wmin=0.2, wmax=1.8, step=0.001, epsilon=0.007):

    ## rms, signal peak position
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

## this function replaces content between the two control strings
def replaced(base, content, starting, ending):

    partitioned_string = base.partition(starting)
    before=partitioned_string[0]
    after=partitioned_string[2]
    partitioned_after=after.partition(ending)
    after=partitioned_after[2]

    final=before+content+after
    return final 



#__________________________________________________________________________________

rt.gROOT.SetBatch(True) ## avoid figures pop out to screen

usage = 'usage: %prog [options]'
parser = optparse.OptionParser(usage)

parser.add_option('-i','--useIso',
                  action="store_true",
                  dest='useIso',
                  default=False,
                  help='true/false multiply by iso ratio in tcl file')

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

object_dict={


              
              'muon':{
                        'collection':'muon',
                        'fit_range':[0.9,1.1],
                        'scale_quality':'looseIDISO', ## collection used for momentum scale and smearing
                        'qualities':['loose','medium','tight'], ## (will look for string "DUMMY_MUON_{quality}ID_EFFICIENCY or DUMMY_MUON_{quality}ID_FAKERATE )
                        'file_prompt_F':'histos/muon_fullsim_LMT012.root',
                        'file_prompt_D':'histos/muon_delphes_v07VAL_withfakes.root',
                        'file_fake_F':'histos/muonfakes_fullsim_LMT012.root',
              },

              'electron':{
                        'collection':'electron',
                        'fit_range':[0.9,1.1],
                        'scale_quality':'looseIDISO', ## collection used for momentum scale and smearing
                        'qualities':['loose','medium','tight'], ## here store qualities used to produce efficiencies and fake-rate (dummy for now)
                        'file_prompt_F':'histos/electron_fullsim_LMT012.root',
                        'file_prompt_D':'histos/electron_delphes_v07VAL_withfakes.root',
                        'file_fake_F':'histos/electronfakes_fullsim_LMT012.root',
                        
              },

              'photon':{
                        'collection':'photon',
                        'fit_range':[0.9,1.1],
                        'scale_quality':'looseIDISO', ## collection used for momentum scale and smearing
                        'qualities':['loose','medium','tight'], ## here store qualities used to produce efficiencies and fake-rate (dummy for now)
                        'file_prompt_F':'histos/photon_fullsim_LMT012.root',
                        'file_prompt_D':'histos/photon_delphes_v07VAL_withfakes.root',
                        'file_fake_F':'histos/photonfakes_fullsim_LMT012.root',
                        
              },

              'jet':{
                        'collection':'jetpuppi',
                        'fit_range':[0.0,2.0],
                        'scale_quality':'tightID', ## collection used for momentum scale and smearing
                        'qualities':['loose','tight'], ## here store qualities used to produce efficiencies and fake-rate (dummy for now)
                        'file_prompt_F':'histos/jetpuppi_fullsim_LMT012.root',
                        'file_prompt_D':'histos/jetpuppi_delphes_v07VAL_withfakes.root',
              },
}


(opt, args) = parser.parse_args()

useIso = opt.useIso


### dump dummy card content into string
with open(opt.card_in, 'r') as f:
    base = f.read()

content=base

for obj, params in object_dict.items():

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
        try:
            test = hf.Integral()
            if test == 0: continue
        except:
            continue

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
            
            print colname, quality, ptmin, ptmax, etamin, etamax

            ## form input ntuple for mean_and_sigmas dictionary
            ntup_in = (colname, quality, ptmin, ptmax, etamin, etamax)

            mean_and_sigmas_d[ntup_in] = get_mean_and_sigma(hd, wmin=fit_range_min, wmax=fit_range_max, step=0.001, epsilon=0.005)
            mean_and_sigmas_f[ntup_in] = get_mean_and_sigma(hf, wmin=fit_range_min, wmax=fit_range_max, step=0.001, epsilon=0.005)


        ### HERE IS WHERE WE COMPUTE EFFICIENCY RATIOS AND FAKE RATE


    ## HERE IS WHERE WE COMPUTE THE VALUES AND DUMP THE RESOLUTION IN THE INPUT TCL FILE 

    ntup_list = mean_and_sigmas_d.keys()

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


        ## compute values to write in delphes card

        mu_d = mean_and_sigmas_d[ntup_in][0]
        mu_f = mean_and_sigmas_f[ntup_in][0]

        ## 1 - is gaussian width and 2 - is effective width
        sigma_d = mean_and_sigmas_d[ntup_in][2]
        sigma_f = mean_and_sigmas_f[ntup_in][2]


        if mu_d > 0. and mu_f > 0.:   ## otherwise pick value from previous bin
            scale = mu_f / mu_d

        ## delphes resolution when morphed to full sim scale

        sigmap_d = sigma_d 
        if mu_f > 0.:
            sigmap_d = sigma_d*scale

        sigma_smear = 1.e-06
        if sigma_f**2 > sigmap_d**2: 
            sigma_smear = math.sqrt(sigma_f**2 - sigmap_d**2)

        #print ptmin, ptmax, etamin, etamax
        #print '{}, {}, {}, {}, {}, {}'.format(mu_f, mu_d, sigma_f, sigma_d, sigmap_d, sigma_smear)

        lines_scale[(coll,quality)].append('   (abs(eta) > {:.1f} && abs(eta) <= {:.1f}) * (pt > {:.1f} && pt <= {:.1f}) * ({:.3f}) +'.format(etamin, etamax, ptmin, ptmax, scale))
        lines_reso[(coll,quality)].append('   (abs(eta) > {:.1f} && abs(eta) <= {:.1f}) * (pt > {:.1f} && pt <= {:.1f}) * ({:.6f}) +'.format(etamin, etamax, ptmin, ptmax, sigma_smear))


    dump_scale=lines_scale[(collection,scale_quality)]
    dump_reso=lines_reso[(collection,scale_quality)]

    dump_scale=clean_dump(dump_scale)
    dump_reso=clean_dump(dump_reso)

    ## HERE REPLACE CONTENT OF THE CARD BETWEEN CONTROL STRINGS 

    ## scale parametrisation
    content=replaced(content, dump_scale, starting_scale, ending_scale)
    
    ## smear parametrisation  
    content=replaced(content, dump_reso, starting_smear, ending_smear)

    ## ADD HERE VARIOUS EFFICIENCIES AND FAKE RATES

    for quality in params['qualities']:

        dumpname='efficiency2D_'+quality+'IDISO'
        
        if collection == 'jetpuppi':
            dumpname='efficiency2D_'+quality+'ID'
            
        name=collection+'_'+dumpname

        form = 'Efficiency'
        print quality, name

        id2D_f = inputFile_f.Get(name).ProjectionXY("id_"+name+"_f")
        id2D_d = inputFile_d.Get(name).ProjectionXY("id_"+name+"_d")

        lines_eff = []
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
                ratio = 1.
                eff_d = id2D_d.GetBinContent(xbin+1,ybin+1)
                eff_f = id2D_f.GetBinContent(xbin+1,ybin+1)
                if eff_d > 0 and eff_f > 0 and eff_f < eff_d: 
                    ratio = eff_f/eff_d

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

        #print dump_eff

        starting_eff = '## DUMMY_' + collection.upper() + '_'+ quality.upper() + 'ID_EFFICIENCY'
        ending_eff = starting_eff.replace('DUMMY','ENDDUMMY')

        content=replaced(content, dump_eff, starting_eff, ending_eff)

        if 'file_fake_F' in params: ## exclude jets

            file_fake_F=params['file_fake_F']
            fakeFile_f = rt.TFile.Open(file_fake_F)

            lines_fake = []
            #lines_fake.append('  ### {} {} FAKE \n'.format(collection,quality))
            
            pdgcode=-1
            if collection=='electron': pdgcode=11
            elif collection=='muon': pdgcode=13
            elif collection=='photon': pdgcode=22
            
            lines_fake.append('  {{{}}} {{\n'.format(pdgcode))

            ### extract fakerate

            name_fake=collection+'_fakerate2D_'+quality+'IDISO'

            ## this is already a TH2
            
            print name_fake
            fake2D_f = fakeFile_f.Get(name_fake)

            ## ex: DUMMY_PHOTONMediumID_EFFICIENCY

            ### calculate residual efficiency
            for ybin in range(0,fake2D_f.GetNbinsY()): ## eta
                isetaOF = False

                if fake2D_f.GetYaxis().GetBinWidth(ybin+1) == 0: continue
                etalow = fake2D_f.GetYaxis().GetBinLowEdge(ybin+1)
                etahigh = fake2D_f.GetYaxis().GetBinUpEdge(ybin+1)
                if etahigh > 10: isetaOF = True

                for xbin in range (0,fake2D_f.GetNbinsX()): ##pt
                    isptOF = False

                    if fake2D_f.GetXaxis().GetBinWidth(xbin+1) == 0: continue
                    ptlow = fake2D_f.GetXaxis().GetBinLowEdge(xbin+1)
                    pthigh = fake2D_f.GetXaxis().GetBinUpEdge(xbin+1)
                    if pthigh > 9e4: isptOF = True

                    eff_f = fake2D_f.GetBinContent(xbin+1,ybin+1)

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

            #print dump_fake

            starting_fake = '## DUMMY_' + collection.upper() + '_'+ quality.upper() + 'ID_FAKERATE'
            ending_fake = starting_fake.replace('DUMMY','ENDDUMMY')

            content=replaced(content, dump_fake, starting_fake, ending_fake)


## dump new content into new delphes card

out_card = open(opt.card_out, "w")
n = out_card.write(content)
out_card.close()


