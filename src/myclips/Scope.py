'''
Created on 19/lug/2012

@author: Francesco Capozzo
'''
from myclips.Observer import Observer
from myclips.TemplatesManager import TemplatesManager
from myclips.GlobalsManager import GlobalsManager
from myclips.FunctionsManager import FunctionsManager
from myclips.RestrictedManager import RestrictedDefinition, RestrictedManager
from myclips.ModulesManager import UnknownModuleError

class Scope(Observer):
    '''
    Describe and give access to all construct available
    in a specific scope/module 
    '''

    PROMISE_TYPE_TEMPLATE = 'deftemplate'
    PROMISE_TYPE_FUNCTION = 'deffunction'
    PROMISE_TYPE_GLOBAL = 'defglobal'
    PROMISE_NAME_ALL = '?ALL'
    PROMISE_NAME_NONE = '?NONE'

    def __init__(self, moduleName, mManager, imports=None, exports=None):
        '''
        Initialize the Scope, create instanced of all
        needed restricted managers of definitions and
        automatically registering this scope in the
        modulesManager. Import and Export are parsed to
        define importable/exportable definition. Promise
        will be used if possible
        
        @raise ScopeDefinitionConflict: if a module import the
            two different definitions with the same name from two modules
        @raise ScopeDefinitionNotFound: trying to import from
            an unknown module? :)
        @raise ValueError: if import/export are not valid instances 
        '''
        self._templates = TemplatesManager(self)
        self._globals = GlobalsManager(self)
        self._functions = FunctionsManager(self)
        self._moduleName = moduleName
        self._moduleManager = mManager
        self._exports = _ScopeExportPromise(exports)
        
        if imports is None:
            imports = []
            
        self._imports = imports
            
        typeMap = {
            Scope.PROMISE_TYPE_TEMPLATE   : self.templates,
            Scope.PROMISE_TYPE_FUNCTION   : self.functions,
            Scope.PROMISE_TYPE_GLOBAL     : self.globalsvars
        }
            
        try:
            
            # imports buffer: i need it
            # because otherwise i will destroy
            # Scope own definition on import ?NONE
            tmp_imports = {}
                
            for imDef in imports:
                if not isinstance(imDef, ScopeImport):
                    raise ValueError("Export definition must be a ScopeExport instance")
                
                assert isinstance(imDef, ScopeImport)
                # first thing: let's check the module
                try:
                    otherModDef = self._moduleManager.getScope(imDef.iModule)
                    
                    otherTypeMap = {
                        Scope.PROMISE_TYPE_TEMPLATE   : otherModDef.templates,
                        Scope.PROMISE_TYPE_FUNCTION   : otherModDef.functions,
                        Scope.PROMISE_TYPE_GLOBAL     : otherModDef.globalsvars
                    }
                    
                    
                except UnknownModuleError:
                    raise ScopeDefinitionNotFound("Unable to find defmodule {0}".format(imDef.iModule))
                else:
                    if imDef.iType == Scope.PROMISE_NAME_NONE:
                        if tmp_imports.has_key(imDef.iModule):
                            del tmp_imports[imDef.iModule]
                        #else it's ok, i don't any def yet
                    else:
                        importQueue = []
                        if imDef.iType == Scope.PROMISE_NAME_ALL:
                            # i have to import everything already defined
                            # and set a listener on the scope
                            # for future definitions
                            importQueue = [Scope.PROMISE_TYPE_FUNCTION, Scope.PROMISE_TYPE_GLOBAL, Scope.PROMISE_TYPE_TEMPLATE]
                        else:
                            importQueue = [imDef.iType]
                        # i know what i have to import now
                        for iqType in importQueue:
                            
                            # get the list of definition i need to import
                            imported = otherModDef.getExports(iqType, imDef.iName)
    
                            # if i haven't imported anything for this module
                            # yet, just create a skeleton dict                        
                            if not tmp_imports.has_key(imDef.iModule):
                                mod_imports = {Scope.PROMISE_TYPE_FUNCTION: {},
                                               Scope.PROMISE_TYPE_GLOBAL: {},
                                               Scope.PROMISE_TYPE_TEMPLATE: {}}
                                tmp_imports[imDef.iModule] = mod_imports
                            else:
                                # otherwise i use the one i already got
                                mod_imports = tmp_imports[imDef.iModule]
    
                            # get the subdict for the import type i need
                            mod_imports = mod_imports[iqType]
                            
                            # time to iterate over every single import definition
                            # if i got a definition with the same name
                            # i raise a ScopeDefinitionConflict,
                            # and abort scope creation this way
                            for (defName, defObj) in imported:
                                if mod_imports.has_key(defName):
                                    raise ScopeDefinitionConflict(("Cannot define defmodule {0} "
                                                                  + "because of an import/export conflict caused by the {0} {1}").format(
                                                        self.moduleName,
                                                        iqType,
                                                        defName
                                                ))
                                else:
                                    # otherwise i definite it and i'm happy
                                    mod_imports[defName] = defObj
                            
                            # if i get a ?ALL definition
                            # i have to add a listner in the other scope
                            # so when there is a new construct definition
                            # the definition is forwarded here
                            if imDef.iName == Scope.PROMISE_NAME_ALL:
                                otherTypeMap[iqType].registerObserver(otherTypeMap[iqType].EVENT_NEW_DEFINITION, self)
            
            # time to merge all imports with the definitions
            # avaiables in the scope
            
            
            for (modName, defDict) in tmp_imports.items():
                for (constType, constDict) in defDict.items():
                    for (defName, defObj) in constDict.items():
                        if typeMap[constType].has(defName):
                            raise ScopeDefinitionConflict(("Cannot define defmodule {0} "
                                                          + "because of an import/export conflict caused by the {0} {2}::{1}").format(
                                                self.moduleName,
                                                constType,
                                                defName,
                                                modName
                                        ))
                        typeMap[constType].addDefinition(defObj)
            
            # all right,
            # include the scope in the MM
            self._moduleManager.addScope(self)
            
        except Exception, mainE:
            # i need to cleanup
            # all listeners
            if len(tmp_imports) > 0:
                for modName in tmp_imports.keys():
                    try:
                        otherModDef = self._moduleManager.getScope(modName)
                        otherModDef.functions.cleanupObserver(self)
                        otherModDef.templates.cleanupObserver(self)
                        otherModDef.globalsvars.cleanupObserver(self)
                    except:
                        continue
            
            # and then raise
            raise mainE

        
            
    def notify(self, eventName, *args, **kargs):
        '''
        Get new definition signal and register definition
        in the right manager for the promise
        @param eventName: the event name
        @type eventName: string
        @param arg[0]: the new definition
        '''
        if eventName == TemplatesManager.EVENT_NEW_DEFINITION:
            self._handleEventNewDefinition(self.templates, args[0])
            
        elif eventName == GlobalsManager.EVENT_NEW_DEFINITION:
            self._handleEventNewDefinition(self.globalsvars, args[0])
            
        elif eventName == FunctionsManager.EVENT_NEW_DEFINITION:
            self._handleEventNewDefinition(self.functions, args[0])
            
    def _handleEventNewDefinition(self, manager, definition):
        '''
        Handle the new definition forwarding to the right manager
        @param manager: the manager to use
        @type manager: RestrictedManager
        @param definition: the definition
        @type definition: RestrictedDefinition
        '''
        
        assert isinstance(definition, RestrictedDefinition)
        assert isinstance(manager, RestrictedManager)
        
        # i need to verify the case (1):
        #    module A import ?ALL module B
        #    module B import ?ALL module A
        # in this case if there is a new definition
        # in A, it is forwarded to B
        # the new addition is then re-forwarded to
        # A itself... In this case, i need to ignore
        # the re-forwarded addition
        if definition.moduleName != self.moduleName:
            # i need to verify the case (2):
            #    module A
            #    module B import ?ALL module A
            #    module C import ?ALL module B and A
            if manager.has(definition.name):
                defPresent = manager.getDefinition(definition.name)
                # I already have a definition with the same name
                # so there is a conflict if they are equals
                if defPresent != definition:
                    raise ScopeDefinitionConflict("Cannot define {1} {0} because of an import/export conflict".format(
                                    definition.name,
                                    definition.definitionType
                                ))
                # otherwise it's ok: i already know about this definition
                # just like in case (2)
            
            else:
                # this is a new definition
                # i need to add this to my scope
                manager.addDefinition(definition)
            
        # otherwise it's ok:
        # <-> inclusion just like in case (1)
        # nothing to do 
        
            
    @property
    def moduleName(self):
        '''
        Get the module name for the scope
        '''
        return self._moduleName
    
    @property
    def modules(self):
        '''
        Get the modulesManager instance for this scope
        '''
        return self._moduleManager
    
    @property
    def templates(self):
        '''
        Get the templates manager
        '''
        return self._templates
    
#    @templates.setter
#    def templates(self, value):
#        self._templates = value
        
    @property
    def globalsvars(self):
        '''
        Get the globals manager
        '''
        return self._globals
    
#    @globalsvars.setter
#    def globalsvars(self, value):
#        self._globals = value

    @property
    def functions(self):
        '''
        Get the functions manager
        '''
        return self._functions


    def isImportable(self, eType, eName):
        '''
        Check if a definition of this scope 
        is importable from an other scope
        @param eType: definition type
        @type eType: string
        @param eName: definition name
        @type eName: string
        '''
        return self._exports.canExport(eType, eName)
    
    def getExports(self, eType, eName=None):
        '''
        Get the list of export definition for this scope
        @param eType: for a type
        @type eType: string
        @param eName: and a def name
        @type eName: string
        '''
        exDefs = self._exports.getExports(eType)
        
        typeMap = {
            Scope.PROMISE_TYPE_TEMPLATE   : self.templates,
            Scope.PROMISE_TYPE_FUNCTION   : self.functions,
            Scope.PROMISE_TYPE_GLOBAL     : self.globalsvars
        }
        
        # check if export all is here!
        if exDefs.has_key(Scope.PROMISE_NAME_ALL):
            # i need to get all definitions i already got
            # and replace the array
            exDefs = dict([(defName, defName) for defName in typeMap[eType].definitions])
        
        if eName is None or eName == Scope.PROMISE_NAME_ALL:
            return [(eName, typeMap[eType].getDefinition(eName)) for eName in exDefs.keys() if eName != Scope.PROMISE_NAME_ALL]
        elif isinstance(eName, list):
            # i want a selection of exports
            return [(dName, typeMap[eType].getDefinition(dName)) for dName in exDefs.keys() if dName in eName]
        else:
            # this ensure the export for the name exists
            # otherwise a KeyError is raised
            exDefs[eName]
            return [(eName, typeMap[eType].getDefinition(eName))]
        
    def __repr__(self):
        return "<" + "::".join((self.__class__.__name__,self.moduleName)) + ">"
        
    def __str__(self, *args, **kwargs):
        retStr = [super(Scope, self).__repr__(*args, **kwargs)]
        TAB = "\t|"
        retStr.append(TAB + "-moduleName: " + self.moduleName)
        retStr.append(TAB + "-exports: ")
        retStr.append(str(self._exports))
        retStr.append(TAB + "-imports: ")
        for im in self._imports:
            retStr.append(TAB + TAB + "-" + str(im))
        
        iMan = [("functions", self.functions),
                ("globals", self.globalsvars),
                ("templates", self.templates)]
        for (aN, aM) in iMan:
            retStr.append(TAB + "-{0}: ".format(aN))
            for iDef in aM.definitions:
                retStr.append(TAB + TAB + "-{0}::{1}".format(
                        aM.getDefinition(iDef).moduleName, 
                        iDef
                    ))
        return "\n".join(retStr)+"\n"
        
        
        
class _ScopeExportPromise(object):
    '''
    Export promise manager for "not definited yet" definitions
    '''
    
    _typeMap = {
            Scope.PROMISE_TYPE_TEMPLATE   : '_pTemplates',
            Scope.PROMISE_TYPE_FUNCTION   : '_pFunctions',
            Scope.PROMISE_TYPE_GLOBAL     : '_pGlobals'
        }
    
    def __init__(self, exports=None):
        if exports == None:
            exports = []
        
        self._pTemplates = {}
        self._pFunctions = {}
        self._pGlobals = {}
            
        for exDef in exports:
            if not isinstance(exDef, ScopeExport):
                raise ValueError("Export definition must be a ScopeExport instance")
            if exDef.eType == Scope.PROMISE_NAME_ALL:
                self._pTemplates[exDef.eName] = exDef
                self._pFunctions[exDef.eName] = exDef
                self._pGlobals[exDef.eName] = exDef
            elif exDef.eType == Scope.PROMISE_NAME_NONE:
                # name is ignored... all must be flushed
                self._pTemplates = {}
                self._pFunctions = {}
                self._pGlobals = {}
            else:
                if exDef.eName == Scope.PROMISE_NAME_NONE:
                    # empty this promise dict type
                    setattr(self, _ScopeExportPromise._typeMap[exDef.eType], {})
                elif isinstance(exDef.eName, list):
                    pDict = getattr(self, _ScopeExportPromise._typeMap[exDef.eType])
                    for rName in exDef.eName:
                        pDict[rName] = ScopeExport(exDef.eType, rName)
                else:
                    pDict = getattr(self, _ScopeExportPromise._typeMap[exDef.eType])
                    pDict[exDef.eName] = exDef
                    
    def canExport(self, eType, eName):
        pDict = getattr(self, _ScopeExportPromise._typeMap[eType])
        return pDict.has_key(Scope.PROMISE_NAME_ALL) or pDict.has_key(eName)
    
    def getExports(self, eType):
        return getattr(self, _ScopeExportPromise._typeMap[eType])

    def __str__(self):
        TAB = "\t|"
        retStr = []
        for eType in _ScopeExportPromise._typeMap.keys():
            retStr.append(TAB + TAB + "-{0}:".format(eType))
            for exDef in self.getExports(eType).keys():
                retStr.append(TAB + TAB + TAB + "-" + exDef)
        return "\n".join(retStr)

class ScopeImport(object):
    '''
    Describe an import definition
    '''

    def __init__(self, importModule, importType, importName):
        '''
        Create the definition
        @param importModule: the module to import to
        @type importModule: string
        @param importType: the def type to import to
        @type importType: string
        @param importName: the def name to import to
        @type importName: string
        '''
        self._importType = importType
        self._importName = importName
        self._importModule = importModule
    
    @property
    def iModule(self):
        '''
        Get the module for this import definition
        @rtype: string        
        '''
        return self._importModule
    
    @property
    def iType(self):
        '''
        Get the definition type for this import definition
        @rtype: string        
        '''
        return self._importType

    @property
    def iName(self):
        '''
        Get the definition name for this import definition
        @rtype: string        
        '''
        return self._importName
    
    def __str__(self, *args, **kwargs):
        return "<ScopeImport: from {0} {1} {2}>".format(self.iModule, self.iType, self.iName)

class ScopeExport(object):
    '''
    Describes an export definition
    '''
    
    def __init__(self, exportType, exportName):
        '''
        Create a new definition
        @param exportType: the definition type
        @type exportType: string
        @param exportName: the definition name
        @type exportName: string
        '''
        self._exportType = exportType
        self._exportName = exportName
    
    @property
    def eType(self):
        '''
        Get the definition type for this export instance
        @rtype: string
        '''
        return self._exportType

    @property
    def eName(self):
        '''
        Get the definition name for this export instance
        @rtype: string
        '''
        return self._exportName

class ScopeDefinitionNotFound(ValueError):
    '''
    Sorry bro, the scope is not valid
    '''

class ScopeDefinitionConflict(Exception):
    '''
    Sorry bro, import two DIFFERENT construct with the same name
    from two DIFFERENT modules. If the definition was the same,
    maybe I.. but.. you know... I can't!!!
    '''
    pass

