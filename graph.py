#!/usr/bin/env python
# Mark Janssen, <average@mit.edu> February 5, 2001

"""Graph class."""

__version__ = "$Revision: 1.9 $"
__author__  = "$Author: average $"
__date__    = "$Date: 2001/10/21 00:09:20 $"

#change a lot of these for loops to use faster map() function (see FAQ and QuickReference)
#remember reduce(lambda x,y: x+y, [1,2,3,4,5]) works for summing all elements...
#also: map/reduce/filter now work with any iterable object (including dictionaries!)
#add persistence
#implementation options:  { id: Vertex(id).{tail:Edge(tail)}}, {Vertex(id):kjSet(Edges)
#  {id: vertex(id)}{id:{Edge(proxy(Vertex(tail)))}; g.add(vertex, VertType=BaseVert), etc..
#having second thoughts about design:  maybe should use a SparseMatrix class (in Numeric module?) for holding
#  connection matrix:  0 for no connection 1 for unweighted graph, or the actual weight in case of weighted graph
#  a separate dictionary (or list/vector?)  for holding actual vertices and indices
#  a second vector would hold the action energy (for Network type)
#  but remember:  premature optimization...
#XXX Use of exceptions for control flow may prevent seeing actual errors.  Perhaps catch exception, plus error string and assert string is as expected

from __future__ import generators

VertexBaseType = dictionary
GraphBaseType = dictionary
EdgeValue = 1

_DEBUG = 1
_PROFILE = 1

#XXX look at graphnew.py and graphprenew.py for unincorporated updates

# {{{ Vertex
class Vertex(VertexBaseType):
    """Vertex holds the set of the vertices of its own outward directed edges.
    Edge values are taken to be arbitrary."""

    __slots__ = ['_graph', '_id']  #Put all Vertex attributes here.  Uses base class' dictionary, instead of creating duplicate

    def __init__(self, graph, id):
        """Create a Vertex object in graph, populated with optional tail(s)."""
        VertexBaseType.__init__(self)
        self._graph = graph  #graph to which this vertex belongs
        self._id = id

    def add(self, tail):
        """Add the tails to Vertex.  Add tails to graph if neeed."""
        if tail==[]: return
        try:  #single tail addition
            if tail not in self:       #in raises TypeError if non-hashable
                self._graph.add(tail)  #add tail vertices to graph
                self[tail] = EdgeValue
        except TypeError:  #multiple tail addition
            self.update(tail)

    def discard(self, tail):
        """Removes tail(s) if present, otherwise does nothing."""
        try: #single tail removal
            del self[tail]
        except LookupError:  return
        except TypeError: #must have been given a tail list
            if not isinstance(tail, list): raise TypeError("argument must be hashable type or a list object.")
            self -= tail

    def update(self, tails):
        """Add list of tails from iterable object to Vertex.  Adds tails to graph if needed."""
        #verify ifinstance(tails,list)? ...don't want to update with a tuple, e.g.
        for t in tails:
            if t not in self:
                self._graph.add(t)  #will assume that if t in self, then t in self._graph
                self[t] = EdgeValue

    def in_vertices(self):
        return self._graph.in_vertices(self._id)

    out_vertices = VertexBaseType.iterkeys
    out_degree = VertexBaseType.__len__

    def _fastupdate(self, tails):
        """Add list of tails without checking for existence in graph."""
        if isinstance(tails, list):
            for t in tails:
                if t not in self:  #probably faster to check if already present, than do redundant assignment
                    self[t] = EdgeValue
        elif tails not in self:
            self[tails] = EdgeValue

    def __isub__(self, other):
        """Remove the given tail vertices.  Other can be any iterable object."""
        for tail in other:  #XXX inefficient if self is near empty
            try:
                del self[tail]
            except LookupError:
                if not len(self): break  #good place to check if self is empty yet...
        return self

    def __str__(self):
        """Return string of tail vertices in set notation."""
        if _DEBUG: self.validate()
        return "{%s| %s}" % (self._id, `self.keys()`[1:-1])

    def __copy__(self):
        """Make a copy of the Vertex: tail set."""
        result = self.__class__(self._graph, self._id)
        dictionary.update(result, self) #XXX shallow copy may cause problems if EdgeValue becomes non-simple!
        return result

    copy = __copy__

    def validate(self):
        """Assert Vertex invariants."""
        assert isinstance(self._graph, BaseGraph)
        hash(self._id) #id should be hashable
        for t in self:
            assert t in self._graph, "Non-existant tail %s in vertex %s" % (t, self._id)
            assert self[t] == EdgeValue, "Bad value on tail %s in vertex %s" % (t, self._id)
# }}} Vertex

# {{{ Graph class
class BaseGraph(GraphBaseType):
    """Basic class implementing a directed Graph.  Vertices without edges are allowed.
    Self-referencing vertices are allowed."""
    #Basic data structure {vertex id: {t1: edge; t2: edge}

    __slots__ = ['VertexType']

    def __init__(self, initgraph=None, VertexType=Vertex):
        """Create the graph, optionally initializing from another graph."""
        GraphBaseType.__init__(self)
        self.VertexType = VertexType
        if initgraph is not None:
            assert isinstance(initgraph, BaseGraph)
            initgraph.validate()
            dictionary.update(self, initgraph)  #XXX this will create shared Vertex objects!

    def add(self, head, tail=[]):
        """Add the vertices and/or edges.
        Parameters can be single vertex or list of vertices.
        If only one parameter is given, then only vertex additions are made.
        If both parameter are given, then edge additions are made.  Vertices are added as necessary.
        """

        if tail!=[]: self.add(tail)
        try:  #simplest possibility first:  single head addition
            if head not in self:
                self[head] = self.VertexType(self, head)
            if tail != []:
                self[head]._fastupdate(tail)
        except TypeError:  #multiple head addition
            if not isinstance(head, list): raise TypeError("argument must be hashable type or a list object.")
            for h in head:
                if h not in self:
                    self[h] = self.VertexType(self, h)
                self[h]._fastupdate(tail)
        if _DEBUG: self.validate()

    def count(self, head, tail=[]):
        return len(self.select(head, tail))

    def select(self, head, tail=[]):
        """Return list of vertices or edge tuples that satisfy constraints given.
        Parameters can be either single vertex names or list of vertices.
        select(All) returns all vertices in graph.
        select(All, All) returns all edges in graph.
        select(h, ALL) returns all edges where h is the head vertex.
        select(ALL, t) return all edges where t is the tail vertex.
        select(v) returns intersection of v and graph.
        select(h,t) returns intersection of (h,t) and all graph edges.
        """
        #XXX if self.vertices() is passed as both parameters, it appears that each affect the other...
        #XXX returns duplicates if parameters contain duplicates
        if not isinstance(head, list) and type(head)!=type(self.iterkeys()): head = [head] #XXX isinstance(head, generator) not work in v2.2a4
        if tail==[]:
            return [h for h in head if h in self]
        else:
            if not isinstance(tail, list) and type(tail)!=type(self.iterkeys()): tail = [tail] #XXX
            return [(h, t) for h in head if h in self for t in tail if t in self[h]]

    def discard(self, head, tail=[]):
        """Remove vertices and/or edges.
        Parameters can be single vertex or list of vertices.
        If tail is non-empty, then only edge deletions are made.
        If tail is empty, then vertex deletions are made and any associated edges.
        """
        if tail==[]:    #vertex deletions
            try:
                del self[head]
            except LookupError: pass   #do nothing if given non-existent vertex
            except TypeError:          #given head list
                if not isinstance(head, list): raise TypeError("argument must be hashable type or a list object.")
                for h in head:
                    if h in self:
                        self[h].clear()
                        GraphBaseType.__delitem__(self, h) #don't duplicate effort (will discard in_vertices below)
                    else: head.remove(h) #for faster tail removal in next loop
                for h in self:   #visit remaining vertices and remove occurances of head items in edge lists
                    self[h].discard(head)
        else:   #edge deletions only
            if not isinstance(head, list): head = [head] #quick and dirty to avoid extra code
            for h in head:
                if h in self:
                    self[h].discard(tail)
        if _DEBUG: self.validate()

    #alternate syntax for various items
    out_vertices = GraphBaseType.__getitem__  #XXX returns dictionary, unlike in_vertices() which returns iterator
    vertices = GraphBaseType.iterkeys
    order = GraphBaseType.__len__
    #__setitem__ #for some reason is called for self[v] -= [tails] so can't remove from interface
    setdefault = None  #XXX this defines an attribute, not re-defines method

    def in_vertices(self, vertex):  #O(n)
        """Return iterator over the vertices where vertex is tail."""
        if vertex not in self:
            raise LookupError(vertex)
        for h in self:
            if vertex in self[h]:
                yield h

    def popitem(self):
        """Remove and return one arbitrary vertex-edge tuple.  Preserve graph invariants."""
        for v, tails in self.iteritems(): break  #XXX any better way?
        tails = tails.copy()  #must make copy since we have the actual object which is about to be deleted.
        del self[v]  #removes any edges as necessary
        return (v, tails)

    def update(self, other):
        """Merges one graph with another.  Takes union of edge lists."""
        assert isinstance(other, BaseGraph), "Can only merge Graph types."
        for h in other:
            if h in self:  #do union of edge sets
                self[h].update(other[h])  #XXX update doesn't currently preserve values
            else:   #otherwise just copy the set
                self[h] = other[h].copy() #XXX copy or deepcopy?

    def __delitem__(self, head):
        """Delete a single vertex and associated edges.
        Raises LookupError if given non-existant vertex."""
        self[head].clear() #removes out vertices
        for v in self.in_vertices(head):
            del self[v][head]
        GraphBaseType.__delitem__(self, head)

    def __str__(self):
        self.validate()
        return '{' + ', '.join(map(str, self.itervalues())) + '}'

    __repr__ = __str__

    def validate(self):
        """Check graph invariants."""
        #NOTE:  calling this after each insert/remove slows things down considerably!
        for v in self.vertices():
            assert isinstance(self[v], self.VertexType), "Vertex type not found on " + str(v)
            self[v].validate()

# }}} Graph

def test(g, size=100):
    import time
#    from graphsupport2 import *
    #FIXME:  should exercise every function in graph...
    #FIXME:  should try removing non-existent things too
    #FIXME:  should try excercise graph.update()
    g.add(0)
    g.add(0,0)
    g.add(1)
    print g.select(g.keys(), g.keys())
    g.add(1)
    g.add(1,0)
    g.add(1,0)
    g.discard(1,0)
    print g
    print "Creating graph of size",size,"..."
    g.add(range(size),range(size))
    g.add(range(size+20,size+40,2))
    g.add(size+1, [1,2,3])
    g.add([3,4,5], size+1)
    print g.select(size+1, g.vertices())
    print g.select(g.vertices(), size+1)
    print len(g)
    print len(g[size+1])
    g.discard(range(50))
    g.discard(1,2)
    g.discard(g.vertices(),3)
    g.validate()
    print "Erasing graph..."
    g.clear()
#    generate(g, "random",30)
#    generate(g, "random",30)
    print g
    if _PROFILE:
        print "Profiling (ignoring debug)..."
        global _DEBUG
        previous = _DEBUG
        _DEBUG = 0
        for i in [1,2]:
            start=time.clock()
            g.add(range(1000),range(1000))
            finish=time.clock()
            print "Add 1000, 1000; pass %i: %5.2fs" %  (i, (finish-start))
        for i in [1,2]:
            start=time.clock()
            g.discard(range(1000), range(100))#, range(1000))
            finish=time.clock()
            print "Discard 1000, 100; pass %i:  %5.2fs" % (i, (finish-start))
        g.clear()
        g.add(0)
        for i in [1,2]:
            start=time.clock()
            g[0].update(range(1000))
            finish=time.clock()
            print "Update 1000, 1000; pass %i:  %5.2fs" % (i, (finish-start))
        _DEBUG = previous
        g.clear()

if __name__ == '__main__':
    g=BaseGraph()
    test(g, 100)
