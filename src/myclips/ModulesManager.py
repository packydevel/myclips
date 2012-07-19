'''
Created on 17/lug/2012

@author: Francesco Capozzo
'''

class ModulesManager(object):
    '''
    Stores the list of allowed functions
    '''
    instance = None

    def __init__(self):
        '''
        Constructor
        '''
        self._modules = {}
        self._currentScope = None
        
    def isDefined(self, moduleName):
        return self._modules.has_key(moduleName)

    def addScope(self, scope):
        if self.isDefined(scope.moduleName):
            raise ValueError("Cannot redefine defmodule {0} while it is in use".format(scope.moduleName))
        self._modules[scope.moduleName] = scope
        self._currentScope = scope
        
    def changeCurrentScope(self, moduleName):
        # this way i get exception if I try to change the scope to
        # and undef module
        try:
            self._currentScope = self._modules[moduleName]
        except KeyError:
            raise ValueError("Unable to find defmodule {0}".format(moduleName))
        
    def getCurrentScope(self):
        return self._currentScope
        
    def getScope(self, moduleName):
        return self._modules[moduleName]
        
    def getModulesNames(self):
        return self._modules.keys()
        
    def reset(self):
        self._modules = {}


# Standard instance
ModulesManager.instance = ModulesManager()