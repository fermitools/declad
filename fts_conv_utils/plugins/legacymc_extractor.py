
from fts.metadata_extractors import BaseMetadataExtractor

class LegacyMC(BaseMetadataExtractor):
    name = "legacy_nova_mc_metadata"

    def extract(self,filestate, *args, **kwargs):

        type_trans = {'sim'      : 'importedSimulated'
                     }
        tier_trans = {'pid'      : 'pid' ,
                      'reco'     : 'reconstructed'
                     }
        swap_trans = {''         : 'none' ,
                      'nonswap'  : 'none' ,
                      'fluxswap' : 'swap' ,
                      'fluxtau'  : 'fluxtau' ,
                      'nueonly'  : 'nueonly' ,
                      '200adc'   : 'none' ,
                      '400adc'   : 'none' ,
                      'rock'     : 'none' ,
                      'eps'      : 'none'
                     }
        hpol_trans = {''         : 'NA' ,
                      'fhc'      : 'fhc' ,
                      'rhc'      : 'rhc'
                     }

        fname = filestate.getFileName()
        fn_m1 = fname.split('_')
        nflds = len(fn_m1)
        fn_m2 = fn_m1[nflds-1].split('.')
        if ( nflds == 11 ):
            hindx = fn_m1[7]
            sindx = fn_m1[8]
        elif ( nflds == 10 ):
            hindx = fn_m1[7]
            sindx = ''
        elif ( nflds == 9 ):
            hindx = ''
            sindx = ''

        novalbl = fn_m1[0] + '_' + fn_m1[5]
        if ( hindx != '' ): novalbl = novalbl + '_' + hindx
        if ( sindx != '' ): novalbl = novalbl + '_' + sindx
        novasub = fn_m1[4][1:]
        if ( novasub != "1" and novasub != "2" ):
            novasub = "1"
            novalbl = novalbl + '_' + fn_m1[4]

        metadata = {
                    'Simulated.detectorID'       : fn_m1[0],
                    'Simulated.firstRun'         : fn_m1[1][1:],
                    'Simulated.firstSubRun'      : fn_m1[2][1:],
                    'Simulated.base_release'     : fn_m1[3],
                    'Simulated.generator'        : fn_m1[5],
                    'Simulated.number_of_spills' : fn_m1[6],
                    'Simulated.horn_polarity'    : hpol_trans[ hindx ],
                    'Simulated.swap'             : swap_trans[ sindx ],
                    'file_type'                  : type_trans[ fn_m2[1] ],
                    'data_tier'                  : tier_trans[ fn_m2[2] ],
                    'file_format'                : fn_m2[3],
                    'runs'                       : [[ int(fn_m1[1][1:]) , 'monte-carlo' ]],
                    'event_count'                : int(fn_m1[6]),
                    'group'                      : 'nova',
                    'NOVA.SubVersion'            : novasub,
                    'NOVA.Label'                 : novalbl,
                    }


        # return directly with the answer
        return metadata


legacymcExtractor = LegacyMC()
