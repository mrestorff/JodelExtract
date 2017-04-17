#!/usr/bin/env python2
# # # # # # # # # # # # # # # # # #
# JodelExtract Configuration File #
# # # # # # # # # # # # # # # # # #

# app version to use when not specified otherwise
APP_VERSION  = '4.41.0'

# General and debugging settings
VERBOSE = True # Print post handling to command line
CONNECTION_VERBOSE = False # Connection actions printing
DEBUG = False # print posts to command line & activate Flask debugger
DBG_NO_IMAGES = False # Disable image download
LOCAL_IMAGE_URLS = True # Get image URLs from local storage

# App name and author for temp directory
APP_NAME = "JodelExtract"
APP_AUTHOR = "MR"

MY_USER_ID = "158813957148f5c32faf16faab738946ba0a16ef"

# Flask database config
DATABASE_PATH = 'tmp/'
USERNAME = ''
PASSWORD = ''

# App key
ANDROID_CLIENT_ID="81e8a76e-1e02-4d17-9ba0-8a7020261b26"
WODEL_CLIENT_ID="6a62f24e-7784-0226-3fffb-5e0e895aaaf"
PORT = 443

SPLASH_TEXT="""
    ###########################################
    ####      Welcome to JodelExtract!     ####
    ###########################################

     ...opening web browser automatically...
"""

def set_config(debug, verbose):
    global CONNECTION_VERBOSE
    global DEBUG
    DEBUG = debug
    CONNECTION_VERBOSE = verbose

class ConfigType():
    """ Just a type to hold the configuration paramters """
    def __init__(self, hmac_secret, version_string=None, user_agent_string=None, x_client_type=None, x_api_version='0.1',client_id=ANDROID_CLIENT_ID):
        # HMAC secret
        #
        # The HMAC secret is generated by the Android app be feeding the
        # signature SHA hash into a native (C++) library.
        # This library changes presumably with every release of the app.
        # The following dictionary contains the HMAC secrets for every version:
        #
        # To calculate this value for yourself, you would need to extract the
        # library from the APK, write a proper Java interface around it, and
        # pass the certificate hash to it.
        if version_string is not None:
            if user_agent_string is None:
                user_agent_string = 'Jodel/'+version_string+' Dalvik/2.1.0 (Linux; U; Android 6.0.1; Nexus 5 Build/MMB29V)'
            if x_client_type is None:
                x_client_type     = 'android_'+version_string

        if hmac_secret is None or len(hmac_secret) != 40:
            raise ValueError('The HMAC secret must be exactely 40 characters long')
        self.hmac_secret = hmac_secret
        self.user_agent = user_agent_string
        self.x_client_type = x_client_type
        self.x_api_version = x_api_version
        self.client_id = client_id


APP_CONFIG={
    '4.27.0': ConfigType('VwJHzYUbPjGiXWauoVNaHoCWsaacTmnkGwNtHhjy', version_string='4.27.0', x_api_version='0.2'),
    '4.28.1': ConfigType('aPLFAjyUusVPHgcgvlAxihthmRaiuqCjBsRCPLan', version_string='4.28.1', x_api_version='0.2'),
    '4.29.0': ConfigType('dIHNtHWOxFmoFouufSflpTKYjPmCIhWUCQHgbNzR', version_string='4.29.0', x_api_version='0.2'),
    '4.29.1': ConfigType('dIHNtHWOxFmoFouufSflpTKYjPmCIhWUCQHgbNzR', version_string='4.29.1', x_api_version='0.2'),
    '4.30.2': ConfigType('zpwKnTvubiKritHEnjOTcTeHxLJJNTEVumuNZqcE', version_string='4.30.2', x_api_version='0.2'),
    '4.31.1': ConfigType('plerFToqEdWlzShdZlTywaCHRuzlKIMsNmOJVDGE', version_string='4.31.1', x_api_version='0.2'),
    '4.32.2': ConfigType('OFIqFvBgkccPNTVbIzkYaSmrwMlbVzRoOBBjXUIG', version_string='4.32.2', x_api_version='0.2'),
    '4.33.2': ConfigType('LDWWpuUigOnKCbCLpoNMDHCqHCWbLKPzHbnIUKIf', version_string='4.33.2', x_api_version='0.2'),
    '4.34.2': ConfigType('SDydTnTdqqaiAMfneLkqXYxamvNuUYOmkqpdiZTu', version_string='4.34.2', x_api_version='0.2'),
    '4.35.6': ConfigType('cYjTAwjdJyiuXAyrMhkCDiVZhshhLhotNotLiPVu', version_string='4.35.6', x_api_version='0.2'),
    '4.37.2': ConfigType('OjZvbmHjcGoPhz6OfjIeDRzLXOFjMdJmAIplM7Gq', version_string='4.37.2', x_api_version='0.2'),
    '4.37.5': ConfigType('NtMEkmHjcGldPDrOfjIeDRzLXOFjMdJmAIpwyFae', version_string='4.37.5', x_api_version='0.2'),
    '4.38.3': ConfigType('KZmLMUggDeMzQfqMNYFLWNyttEmQgClvlPyACVlH', version_string='4.38.3', x_api_version='0.2'),
    '4.40.1': ConfigType('XcpPpQcnfqEweoHRuOQbeGrRryHfxCoSkwpwKoxE', version_string='4.40.1', x_api_version='0.2'),
    '4.41.0': ConfigType('hFvMqLauMtnodakokftuKETbIsVLxpqfjAXiRoih', version_string='4.41.0', x_api_version='0.2'),
    'wodel':  ConfigType('bgulhzgo9876GFKgguzTZITFGMn879087vbgGFuz', x_client_type='wodel_1.1', user_agent_string ='Jodel/1.1 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)', x_api_version='0.2', client_id=WODEL_CLIENT_ID)
};


CAPTCHA_DICT={
    '18FTBXVIJC' : {'md5': '4d97884c3806a531ddb7288bf0eab418', 'solution': [1, 3, 5]},
    '1CEAFRH69O' : {'md5': '08116dcafc684462ea1948819475a81c', 'solution': [7, 8]   },
    '2QT6JRL06T' : {'md5': '389aa660266f0a8f76b5ef21c60cf6fd', 'solution': [1, 2]   },
    '4GEIEE5P8P' : {'md5': '42c904d3cd20f55405a64fcf8032b92a', 'solution': [2, 6, 8]},
    '5VI2JTJYWY' : {'md5': '2a819973e9e6e22eeb445f548201ab40', 'solution': [0, 5]   },
    '6UHC4L53DG' : {'md5': '4d9a9b459f0d3c67581c4990bda3257a', 'solution': [0, 2, 3]},
    'AKWROEYSD3' : {'md5': '2be5ec6995af4925299ed2fa635e4782', 'solution': [1, 5, 7]},
    'BL5901E1JS' : {'md5': '61e0c2f52d510cc89b7432da01494a68', 'solution': [0, 4]   },
    'BNB1P58AJ6' : {'md5': '2ea52cb78ba770b72149daa428331e98', 'solution': [4]      },
    'CORKCXU0TA' : {'md5': '55bd1a0cc31c4d57654d927ca05b81a4', 'solution': [2, 4, 5]},
    'D3SKGYMB0C' : {'md5': '681f0615747ba54f97040ef36dd2e6a0', 'solution': [1]      },
    'DB96PZYUM7' : {'md5': '4fed27abf3b4fa6dad5cf1d852114a1e', 'solution': [2, 7]   },
    'EJSHC2LTY1' : {'md5': '549f069a0189e73f43640a10f7be0de2', 'solution': [5, 6, 8]},
    'G6X12MP9DW' : {'md5': 'd09f368da26b9ed9d583d61f0dd4b1dd', 'solution': [3]      },
    'IGDPXAFRE8' : {'md5': '2224eef78d48f63536bc7e0730ebfd54', 'solution': [1, 6, 7]},
    'IH92Z2ETIE' : {'md5': '5055db4cab5e09eeeac0293ca44ebf65', 'solution': [1, 2, 7]},
    'JGA66GP5TG' : {'md5': '76a3a9ced6474f3db148568d2f396dd6', 'solution': [1, 5, 8]},
    'KUD8PU6UAB' : {'md5': '50abf6c375ea3115168da3be0acc5485', 'solution': [5]      },
    'MF7ZX46TQQ' : {'md5': '9329c0fecaece67da26a740d3519970b', 'solution': [0, 1, 8]},
    'MFDV8CMHHG' : {'md5': 'b04955d8598980df71c7b69ea3a8e7a2', 'solution': [2, 7, 8]},
    'MI9R8R1YIZ' : {'md5': '2ba5296ea4cb4bcd302f5a3b624ecf82', 'solution': [1, 7, 8]},
    'NI1A0RU1VJ' : {'md5': '93af8a552ecf9729493b5c9fea98c748', 'solution': [3, 4, 6]},
    'OFJP966MXD' : {'md5': '5b9a9ae117ebe53e71d236ea3952b974', 'solution': [1, 4, 6]},
    'OQZBADCV8I' : {'md5': 'b435d7145639469b151a6b01a0bfe1c6', 'solution': [2, 5, 8]},
    'QNLPAJ8XGM' : {'md5': '0635a32edc11e674f48dbbfbae98c969', 'solution': [3, 7, 8]},
    'RXNR1VZPUC' : {'md5': '18eaa52fcf87e47edd684c8696aa1798', 'solution': [0, 4, 6]},
    'YLJB76EJDY' : {'md5': '49a857ed6a90225b7de5b9ed22ee2c8a', 'solution': [3, 4]   },
    'YO9E3X95IG' : {'md5': '3f86e8960a64f884aa45ecb696890f5c', 'solution': [0, 1, 8]},
    'ZJP7PW2LRG' : {'md5': 'e785f87dec2b23818dbb8892ea48f91d', 'solution': [4, 5]   },
};
