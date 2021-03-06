'''
Created on 24/lug/2012

@author: Francesco Capozzo
'''
from myclips.rete.nodes.NccPartnerNode import NccPartnerNode
from myclips.rete.Token import Token
from myclips.rete.Node import Node
from myclips.rete.Memory import Memory
from myclips.rete.BetaInput import BetaInput

class NccNode(Node, Memory, BetaInput):
    '''
    Left part of the Ncc/NccPartner duo
    for negative condition of a subconditions chain
    This node act like a beta memory: store activations
    from the left parent and try to combine it
    with items from the right parent (which is a
    ncc-partner-node)
    
    Ncc/NccPartner are a special composition of nodes
    because negation of multiple condition requires
    a node to get left activations from 2 different 
    left parent. To avoid double parent, ncc parent is
    used to convert one of the parent as a right input
    for the ncc main node
    '''


    def __init__(self, leftParent, rightParent, partnerCircuitLength):
        '''
        Create the new ncc node
        '''
        Node.__init__(self, rightParent=None, leftParent=leftParent)
        Memory.__init__(self)
        
        self._partner = NccPartnerNode(rightParent, partnerCircuitLength, self)
        
        
    def leftActivation(self, token, wme):
        
        # combine match in new token
        token = Token(self, token, wme)
        
        # store it inside the local memory
        self.addItem(token)
        
        # get the token stored in the partner node
        # (getFlushBuffer automatically flush the buffer)
        for pToken in self.partner.getFlushResultsBuffer():
            # and link them to this token as ncc result
            # (and link this token as their nccOnwer:
            #    this is done automaticcaly inside the
            #    linkNccResult method
            # )
            token.linkNccResult(pToken)
        
        # i can propagate the token ONLY if
        # not ncc results are linked to this token
        if not token.hasNccResults():
            for child in self.children:
                child.leftActivation(token, None)
        
    def delete(self, notifierRemoval=None, notifierUnlinking=None):
        """
        Remove this node and the partner from the network
        """
        # notify unlink between ncc and partner
        #EventManager.trigger(EventManager.E_NODE_UNLINKED, self.get_partner(), self)
        # then destroy the partner
        self.partner.delete(notifierRemoval, notifierUnlinking)
        # and last destroy this node itself
        Memory.delete(self)
        Node.delete(self, notifierRemoval, notifierUnlinking)
        
    def updateChild(self, child):
        """
        Propagate activation to a child
        only if no ncc-result is found
        for each activation
        """
        for token in self.items:
            if not token.hasNccResults():
                child.leftActivation(token, None)
        
    @property
    def partner(self):
        return self._partner
    
    
    def __str__(self, *args, **kwargs):
        return "<{0}: left={2}, right={3}, children={4}, items={5}, partner={6}>".format(
                        self.__class__.__name__,
                        str(id(self)),
                        str(id(self.leftParent)) if not self.isLeftRoot() else "None",
                        str(id(self.rightParent)) if not self.isRightRoot() else "None",
                        len(self.children),
                        len(self._items),
                        str(id(self.partner)) if self.partner is not None else "None"
                    )
        
    