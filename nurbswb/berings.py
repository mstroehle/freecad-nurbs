'''
create curves and faces like Bezier format 
'''

import numpy as np
import Draft,Points,Part,Sketcher
import nurbswb.say
from nurbswb.say import *
import random
import time


def AA():
	'''dummy method for testing'''
	print "AA-nip"

def BB():
	'''dummy method for testing'''
	print "BB-nip"



import inspect
reload (nurbswb.say)

from nurbswb.miki_g import createMikiGui2, MikiApp
reload( nurbswb.miki_g)

import nurbswb.configuration
reload (nurbswb.configuration)
from nurbswb.configuration import getcf,getcb



def checkcurve(curve):
	'''check the curve to be a supported bezier curve'''
	try:
		assert curve.Degree <= 3
		kns= curve.getMultiplicities()
		if curve.Degree == 3:
			assert kns[0] == 4 and kns[-1]== 4  
			assert min(kns[1:-1])==3 and max(kns[1:-1])==3
		if curve.Degree == 2:
			assert kns[0] == 3 and kns[-1]== 3
			assert len(kns)==2  
		if curve.Degree == 1:
			assert kns[0] == 2 and kns[-1]== 2
			assert len(kns)==2  
	except:
		sayexc("checkcurve results")
		sayexc2("checkcurve Error","assertion failed")


##\cond
class FeaturePython:
	''' basic defs'''

	def __init__(self, obj):
		obj.Proxy = self
		self.Object = obj
		obj.addProperty("App::PropertyBool","_noExecute",'zzz')
		obj.addProperty("App::PropertyBool","_debug",'zzz')

	def attach(self, vobj):
		self.Object = vobj.Object

	def __getstate__(self):
		return None

	def __setstate__(self, state):
		return None


class ViewProvider:
	''' basic defs '''

	def __init__(self, obj):
		obj.Proxy = self
		self.Object = obj

	def __getstate__(self):
		return None

	def __setstate__(self, state):
		return None
##\endcond

def copySketch(sketch,target):
	'''kopiert sketch geometry und constraints into trarget sketch'''
	sb=sketch
	gs=sb.Geometry
	cs=sb.Constraints

	sk=target
	sk.deleteAllGeometry()

	for g in gs:
		rc=sk.addGeometry(g)
		sk.setConstruction(rc,g.Construction)

	for c in cs:
		rc=sk.addConstraint(c)

	sk.solve()
	sk.recompute()
	App.activeDocument().recompute()


class Bering(FeaturePython):
	'''special bezier curve'''

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyInteger","level")
		obj.addProperty("App::PropertyLink","source")
		obj.addProperty("App::PropertyInteger","start")
		obj.addProperty("App::PropertyInteger","end")
		obj.addProperty("App::PropertyFloat","scale").scale=1.0
		obj.addProperty("App::PropertyBool","detach").detach
		obj.addProperty("App::PropertyBool","cyclic")
		obj.addProperty("App::PropertyBool","inverse")
		obj.addProperty("App::PropertyFloatList","extraKnots") #.extraKnots=[0.2,0.4]
		obj.addProperty("App::PropertyEnumeration","mode").mode=['curve','poles','compound']


#	def onChanged(self, fp, prop):
#		pass


	def execute(self,fp):

		if fp.cyclic:
			# make a cyclic bezier chain from the points of the source polygon

			bc=Part.BSplineCurve()

			pts=[v.Point for v in fp.source.Shape.Vertexes]
			pts=pts[1:]+pts[:1]
			l=len(pts)+3
			try: 
				assert l%3 == 0
			except:
				sayexc2(
					"error number of vertexes",
					"for a cyclic Bering 3n points are required not valid source:" + fp.source.Label 
					)

			ms=[3]*(l/3)
			ks=range(len(ms))
			bc.buildFromPolesMultsKnots(pts,ms,ks,True,3)
			fp.Shape=bc.toShape()
			return

		if fp.detach: #use the own data instead of the source
			ptsa=[fp.getPoint(g,1) for g  in range(len(fp.Geometry))]
			ptsa +=[fp.getPoint(len(fp.Geometry)-1,2)]
		else:
			try:
				ptsa=fp.source.Shape.Curve.getPoles()
			except:
				ptsa=[v.Point*fp.scale for v in fp.source.Shape.Vertexes]

		print len(ptsa)



		# testen ob geschlossenes oder offnes modell
		if len(ptsa)%3 == 2:
			sayexc2(
					"error number of vertexes",
					"for a Bering 3n or 3n+1 points are required not valid source:" + fp.source.Label 
				)

		if len(ptsa)%3==0:
			# pts=ptsa[1:]+[ptsa[0],ptsa[1]]
			pts=ptsa+[ptsa[0]]
		else:
			pts=ptsa

		if fp.start==0 and fp.end==0:
			ecken=(len(pts))/3-1

		if fp.end>0:
			ecken=fp.end-fp.start-1
			pts=pts[fp.start*3:fp.start*3+ecken*3+4]
			print(fp.start*3,ecken*3+4)

		ms=[4]+[3]*ecken+[4]

		if fp.inverse:
				pts=pts[::-1]

		bc=Part.BSplineCurve()
		bc.buildFromPolesMultsKnots(pts, ms, range(len(ms)), False,3)

		if 1 or not fp.detach: 
			for i in fp.extraKnots:
					print "knot ",i
					bc.insertKnot(i,3)

		if fp.mode == 'compound':
			comp=[Part.makePolygon(bc.getPoles()),bc.toShape()]
			fp.Shape=Part.Compound(comp)
			return

		if fp.mode == 'poles':
			fp.Shape=Part.makePolygon(bc.getPoles())
			return

		fp.Shape=bc.toShape()
		
		# create the inner geometry
		try:
			if not fp.detach:
				pts=bc.getPoles()
				print pts[0:4]
				pm=fp.source.Placement
				rot=pm.Rotation
				pts=[rot.multVec(p) for p in pts]
				fp.deleteAllGeometry()
				for  i in range(len(pts)-1):
					fp.addGeometry(Part.LineSegment(pts[i],pts[i+1]),False)
				for  i in range(len(pts)-2):
					fp.addConstraint(Sketcher.Constraint('Coincident',i,2,i+1,1)) 
		except:
			print "probleme mot sketch erstellung"
			pass


class Beface(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLinkList","berings")
		obj.addProperty("App::PropertyInteger","start")
		obj.addProperty("App::PropertyInteger","end")
		obj.addProperty("App::PropertyBool","showStripes")
		obj.addProperty("App::PropertyBool","generatedBackbone")



	def execute(self,fp):

#		assert (len(fp.berings)-1)%3==0
		
		ptsa=[]
		ll=-1
		for r in fp.berings:
			pps=r.Shape.Edge1.Curve.getPoles()
			if ll==-1:ll=len(pps)
			assert ll == len(pps)
			ptsa += [pps]

		poles=np.array(ptsa)
#		print ptsa
#		print poles
		print poles.shape

		af=Part.BSplineSurface()
		(a,b,c)=poles.shape

		if not fp.generatedBackbone:
			ecken=(a-1)/3

			if fp.end>0:
				ecken=fp.end-fp.start
				poles=poles[3*fp.start:3*fp.end+1]

			ya=[4]+[3]*(ecken-1)+[4]

			(a,b,c)=poles.shape
			print ("poles.shape a,b",a,b)

			# die bezier variante
			yb=fp.berings[0].Shape.Edge1.Curve.getMultiplicities()

			db=min(3,a-1)
			if db==3:
				ya=[4]+[3]*(ecken-1)+[4]
			if db==2:
				ya=[3,3]
			if db==1:
				ya=[2,2]

		else:
			ya=[4]+[1]*(a-4)+[4]
			yb=fp.berings[0].Shape.Edge1.Curve.getMultiplicities()
			db=3

		af.buildFromPolesMultsKnots(poles, 
				ya,yb,
				range(len(ya)),range(len(yb)),
				False,False,db,3)


		for i in range(1,len(ya)-1):
			if ya[i]<3:
				af.insertUKnot(i,3,0)








		fp.Shape=af.toShape()

		if fp.showStripes:

			wist=20 # width of the tangent stripes

			# create some extra objects for debugging

			#for j in [2,5]:
			for jj in range((a-1)/3-1):
				j=jj*3+2
				pp=poles[j:j+3]
				#normalize and scale the tangents
				ppy=[]
				for (pa,pb,pc) in pp.swapaxes(0,1):
					pa=FreeCAD.Vector(pa)
					pb=FreeCAD.Vector(pb)
					pc=FreeCAD.Vector(pc)
					ppy += [[pb+(pa-pb).normalize()*wist,pb,pb+(pc-pb).normalize()*wist]]

				pp=np.array(ppy).swapaxes(0,1)

				ag=Part.BSplineSurface()
				ag.buildFromPolesMultsKnots(pp, 
						[2,1,2],yb,
						[0,1,2],range(len(yb)),
						False,False,1,3)

				name="rib_tangstrip_"+str(j)

				tt=App.ActiveDocument.getObject(name)
				if tt==None:
					tt=App.ActiveDocument.addObject('Part::Spline',name)
				tt.Shape=ag.toShape()
				tt.ViewObject.ControlPoints = True
				tt.ViewObject.ShapeColor=(1.0,0.0,0.0)


			for j in [0]:
				pp=poles[j:j+2]
				ppy=[]

				for (pa,pb) in pp.swapaxes(0,1):
					pa=FreeCAD.Vector(pa)
					pb=FreeCAD.Vector(pb)
					ppy += [[pa,pa+(pb-pa).normalize()*2*wist]]

				pp=np.array(ppy).swapaxes(0,1)

				ag=Part.BSplineSurface()
				ag.buildFromPolesMultsKnots(pp, 
						[2,2],yb,
						[0,1],range(len(yb)),
						False,False,1,3)

				name="rib_tangstrip_"+str(j)

				tt=App.ActiveDocument.getObject(name)
				if tt==None:
					tt=App.ActiveDocument.addObject('Part::Spline',name)

				tt.Shape=ag.toShape()
				tt.ViewObject.ControlPoints = True
				tt.ViewObject.ShapeColor=(1.0,0.0,0.0)

			for j in [a-2]:
				pp=poles[j:j+2]
				ppy=[]

				for (pa,pb) in pp.swapaxes(0,1):
					pa=FreeCAD.Vector(pa)
					pb=FreeCAD.Vector(pb)
					ppy += [[pb+(pa-pb).normalize()*2*wist,pb]]

				pp=np.array(ppy).swapaxes(0,1)

				ag=Part.BSplineSurface()
				ag.buildFromPolesMultsKnots(pp, 
						[2,2],yb,
						[0,1],range(len(yb)),
						False,False,1,3)

				name="rib_tangstrip_"+str(j)

				tt=App.ActiveDocument.getObject(name)
				if tt==None:
					tt=App.ActiveDocument.addObject('Part::Spline',name)
				tt.Shape=ag.toShape()
				tt.ViewObject.ControlPoints = True
				tt.ViewObject.ShapeColor=(1.0,0.0,0.0)

			#create the meridians
			poles2=poles.swapaxes(0,1)

			for jj in range((b-1)/3-1):
				j=jj*3+2

	#		for j in [2,5,8]:
				pp=poles2[j:j+3]
				ppy=[]
				for (pa,pb,pc) in pp.swapaxes(0,1):
					pa=FreeCAD.Vector(pa)
					pb=FreeCAD.Vector(pb)
					pc=FreeCAD.Vector(pc)
					ppy += [[pb+(pa-pb).normalize()*wist,pb,pb+(pc-pb).normalize()*wist]]
				
				pp=np.array(ppy).swapaxes(0,1)

				ag=Part.BSplineSurface()
				ag.buildFromPolesMultsKnots(pp, 
						[2,1,2],ya,
						[0,1,2],range(len(ya)),
						False,False,1,3)
				name="meridian_tangstrip_"+str(j)
				tt=App.ActiveDocument.getObject(name)
				if tt==None:
					tt=App.ActiveDocument.addObject('Part::Spline',name)
				tt.Shape=ag.toShape()
				tt.ViewObject.ControlPoints = True
				tt.ViewObject.ShapeColor=(.0,0.0,1.0)


			for j in [b-2]:
				pp=poles2[j:j+2]

				ppy=[]
				for (pa,pb) in pp.swapaxes(0,1):
					pa=FreeCAD.Vector(pa)
					pb=FreeCAD.Vector(pb)
					ppy += [[pb+(pa-pb).normalize()*2*wist,pb]]
				
				pp=np.array(ppy).swapaxes(0,1)

				ag=Part.BSplineSurface()
				ag.buildFromPolesMultsKnots(pp, 
						[2,2],ya,
						[0,1],range(len(ya)),
						False,False,1,3)
				name="meridian_tangstrip_"+str(j)
				tt=App.ActiveDocument.getObject(name)
				if tt==None:
					tt=App.ActiveDocument.addObject('Part::Spline',name)
				tt.Shape=ag.toShape()
				tt.ViewObject.ControlPoints = True
				tt.ViewObject.ShapeColor=(.0,0.0,1.0)

			for j in [0]:
				pp=poles2[j:j+2]

				ppy=[]
				for (pa,pb) in pp.swapaxes(0,1):
					pa=FreeCAD.Vector(pa)
					pb=FreeCAD.Vector(pb)
					ppy += [[pa,pa+(pb-pa).normalize()*2*wist]]
				
				pp=np.array(ppy).swapaxes(0,1)

				ag=Part.BSplineSurface()
				ag.buildFromPolesMultsKnots(pp, 
						[2,2],ya,
						[0,1],range(len(ya)),
						False,False,1,3)
				name="meridian_tangstrip_"+str(j)
				tt=App.ActiveDocument.getObject(name)
				if tt==None:
					tt=App.ActiveDocument.addObject('Part::Spline',name)
				tt.Shape=ag.toShape()
				tt.ViewObject.ControlPoints = True
				tt.ViewObject.ShapeColor=(.0,0.0,1.0)


	def execute(self,fp):
		print "ZACK"
		# variante mit drei rippen

#		assert (len(fp.berings)-1)%3==0
		
		ptsa=[]
		ll=-1
		for r in fp.berings:
			pps=r.Shape.Edge1.Curve.getPoles()
			if ll==-1:ll=len(pps)
			assert ll == len(pps)
			ptsa += [pps]

		poles=np.array(ptsa)
#		print ptsa
#		print poles
		print poles.shape

#		poles2=[poles[0],poles[1]+[0,-10,0],poles[1],poles[1]+[0,10,0],poles[-1]]
#		poles=np.array(poles2)

		af=Part.BSplineSurface()
		(a,b,c)=poles.shape

		if not fp.generatedBackbone:
			ecken=(a-1)/3

			if fp.end>0:
				ecken=fp.end-fp.start
				poles=poles[3*fp.start:3*fp.end+1]

			ya=[4]+[3]*(ecken-1)+[4]

			(a,b,c)=poles.shape
			print ("poles.shape a,b",a,b)

			# die bezier variante
			yb=fp.berings[0].Shape.Edge1.Curve.getMultiplicities()

			db=min(3,a-1)
			if db==3:
				ya=[4]+[3]*(ecken-1)+[4]
			if db==2:
				ya=[3,3]
			if db==1:
				ya=[2,2]

		else:
			ya=[4]+[1]*(a-4)+[4]
			yb=fp.berings[0].Shape.Edge1.Curve.getMultiplicities()
			db=3

		print ya
		print yb
		print poles.shape
		print db

		af.buildFromPolesMultsKnots(poles, 
				ya,yb,
				range(len(ya)),range(len(yb)),
				False,False,db,3)


		for i in range(1,len(ya)-1):
			if ya[i]<3:
				af.insertUKnot(i,3,0)






		fp.Shape=af.toShape()







def genk(start,ende,scale,pos,source,show=True):
	# kurven erzeugen
	sk=App.ActiveDocument.addObject('Sketcher::SketchObjectPython','BeringSketch')
	if not show: sk.ViewObject.hide()
	Bering(sk)
	ViewProvider(sk.ViewObject)
	sk.source=source
	sk.start=start
	sk.end=ende
	sk.scale=scale
	sk.Placement.Base=pos
	#App.activeDocument().recompute()
	return sk


def genA():

	source=App.ActiveDocument.Sketch002;end=2;start=0
	source=App.ActiveDocument.Sketch003;end=5;start=0

	sks=[]

	sks += [genk(start,end,1,FreeCAD.Vector(),source)]
	sks += [genk(start,end,1.9,FreeCAD.Vector(200,0,0),source)]
	sks += [genk(start,end,0.9,FreeCAD.Vector(400,0,100),source)]


	sf=App.ActiveDocument.addObject('Sketcher::SketchObjectPython','BeringFace')
	Beface(sf)
	sf.berings=sks
	ViewProvider(sf.ViewObject)

	App.activeDocument().recompute()



	# varianten zum testen
def genB():

		#source=App.ActiveDocument.Sketch;end=5:start=1
	source=App.ActiveDocument.Sketch001;end=0;start=0

	sks=[]

	sks += [genk(start,end,1,FreeCAD.Vector(),source)]
	sks += [genk(start,end,0.9,FreeCAD.Vector(0,0,80),source)]

	sks += [genk(start,end,0.5,FreeCAD.Vector(0,0,200),source)]
	sks += [genk(start,end,0.5,FreeCAD.Vector(0,0,240),source)]
	sks += [genk(start,end,0.5,FreeCAD.Vector(0,0,280),source)]

	sks += [genk(start,end,0.6,FreeCAD.Vector(0,0,600),source)]
	sks += [genk(start,end,0.6,FreeCAD.Vector(0,0,650),source)]
	sks += [genk(start,end,0.6,FreeCAD.Vector(0,0,690),source)]

	sks += [genk(start,end,0.64,FreeCAD.Vector(0,0,800),source)]
	sks += [genk(start,end,0.64,FreeCAD.Vector(0,0,850),source)]
	sks += [genk(start,end,0.64,FreeCAD.Vector(0,0,890),source)]

	sks += [genk(start,end,1.1,FreeCAD.Vector(0,0,1340),source)]
	sks += [genk(start,end,1.0,FreeCAD.Vector(0,0,1440),source)]

	sf=App.ActiveDocument.addObject('Sketcher::SketchObjectPython','BeringFace')
	Beface(sf)
	sf.berings=sks
	ViewProvider(sf.ViewObject)

	App.activeDocument().recompute()

def createBering():
	'''create Bering Sketches for selected objects'''
	for source in Gui.Selection.getSelection():
		genk(0,0,1,FreeCAD.Vector(),source)


def AA():
	obj=App.ActiveDocument.jj2
	sf=obj.Shape.Face1.Surface
	poles=np.array(sf.getPoles())
	print poles.shape
	u=2
	v=2
	sub=poles[u:u+9,v:v+6]
	t1=1
	t2=1


	sub[:]=(t1*sub[1]+t2*sub[4])/(t1+t2)

	poles[u:u+9,v:v+6]=sub
	af=Part.BSplineSurface()
	af.buildFromPolesMultsKnots(poles, 
				sf.getUMultiplicities(),sf.getVMultiplicities(),
				sf.getUKnots(),sf.getVKnots(),
				False,False,sf.UDegree,sf.VDegree)

	#sk=App.ActiveDocument.getObject(res.Name+"_"+label)
	sk=None
	if sk==None:
		sk=App.ActiveDocument.addObject('Part::Spline',"UUU")
		sk.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)

	sk.Shape=af.toShape()

def createBeface():

	sks=Gui.Selection.getSelection()
	sf=App.ActiveDocument.addObject('Sketcher::SketchObjectPython','BeringFace')
	Beface(sf)
	sf.berings=sks
	ViewProvider(sf.ViewObject)


def createBeringTest():

	try:
		App.closeDocument("bering_testdaten")
	except:
		pass

	appdat=FreeCAD.ConfigGet('UserAppData')
	fn=appdat+'/FreeCAD_testfiles/bering_testdaten.fcstd'

	FreeCAD.open(fn)
	App.setActiveDocument("bering_testdaten")
	App.ActiveDocument=App.getDocument("bering_testdaten")
	Gui.ActiveDocument=Gui.getDocument("bering_testdaten")

	genA()
	#genB()

	source=App.ActiveDocument.Sketch004;end=5;start=0

	sks=[]

	sks += [genk(start,end,1,FreeCAD.Vector(),source)]
	sks += [genk(start,end,1.9,FreeCAD.Vector(200,0,0),source)]
	sks += [genk(start,end,0.9,FreeCAD.Vector(400,0,100),source)]


	sf=App.ActiveDocument.addObject('Sketcher::SketchObjectPython','BeringFace')
	Beface(sf)
	sf.berings=sks
	ViewProvider(sf.ViewObject)

	App.activeDocument().recompute()
	connectFaces()
	App.activeDocument().recompute()





def connectFacesAA():
	import numpy as np
	# connect
	sfa=App.ActiveDocument.BeringFace.Shape.Face1.Surface
	pa0=sfa.getPoles()

	sfb=App.ActiveDocument.BeringFace001.Shape.Face1.Surface
	pb0=sfb.getPoles()
	
	_connectFaces(App.ActiveDocument.BeringFace,App.ActiveDocument.BeringFace001)


class Corner(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLink","sourceA")
		obj.addProperty("App::PropertyLink","sourceB")
		obj.addProperty("App::PropertyLink","sourceC")
		obj.addProperty("App::PropertyInteger","modeA","Base")
		obj.addProperty("App::PropertyInteger","modeB","Base")
		obj.addProperty("App::PropertyInteger","modeC","Base")
		ViewProvider(obj.ViewObject)

	def execute(proxy,obj):
		comps=_moveCorner(obj)
		# comps=[obj.sourceA.Shape,obj.sourceB.Shape,obj.sourceC.Shape,]
		obj.Shape=Part.Compound(comps)
		

	def onChanged(self, obj, prop):
		print ("onChanged",prop)
		if prop=="Shape":return
		try:
			comps=[obj.sourceA.Shape,obj.sourceB.Shape,obj.sourceC.Shape,]
		except:
			comps=[]
		if prop in ['modeA','modeB','modeC']:
#			pts= [
#					obj.sourceA.Points[obj.modeA],
#					obj.sourceB.Points[obj.modeB],
#					obj.sourceC.Points[obj.modeC],
#					obj.sourceA.Points[obj.modeA],
#				]
#			ww=Part.makePolygon(pts)
			ss=Part.Sphere()
			ss.Radius=100
			ss.Radius=10
			sa=ss.toShape()
			
			sa.Placement.Base=_moveCorner(obj,True)
			comps += [sa]
			obj.Shape=Part.Compound(comps)






def _fixCorner(a,b,c):

	res=App.ActiveDocument.addObject("Part::FeaturePython","Corner")
	res.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	res.ViewObject.Visibility=False
	Corner(res)

	res.sourceA=a
	res.sourceB=b
	res.sourceC=c



	return

def _moveCorner(res,onlypos=False):

	a=res.sourceA
	b=res.sourceB
	c=res.sourceC
	
	modtab=[[0,0],[0,-1],[-1,0],[-1,-1]]
	[ua,va] = modtab[res.modeA%4]
	[ub,vb] = modtab[res.modeB%4]
	[uc,vc] = modtab[res.modeC%4]

	sfa=a.Shape.Face1.Surface
	pa0=np.array(sfa.getPoles())

	sfb=b.Shape.Face1.Surface
	pb0=np.array(sfb.getPoles())

	sfc=c.Shape.Face1.Surface
	pc0=np.array(sfc.getPoles())


	corner=(pa0[ua,va]+pb0[ub,vb]+pc0[uc,vc])/3.
	if onlypos:
		return corner

	cfg=[['A',sfa,ua,va],['B',sfb,ub,vb],['C',sfc,uc,vc]]
	fs=[]
	
	for (label,sf,u,v) in cfg:
		af=Part.BSplineSurface()
		poles=np.array(sf.getPoles())
		poles[u,v]=corner

		af.buildFromPolesMultsKnots(poles, 
				sf.getUMultiplicities(),sf.getVMultiplicities(),
				sf.getUKnots(),sf.getVKnots(),
				False,False,sf.UDegree,sf.VDegree)

		sk=App.ActiveDocument.getObject(res.Name+"_"+label)
		if sk==None:
			sk=App.ActiveDocument.addObject('Part::Spline',res.Name+"_"+label)
			sk.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)

		sk.Shape=af.toShape()
		fs += [sk.Shape]

	return fs



class Product(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLink","uSource")
		obj.addProperty("App::PropertyLink","vSource")
		obj.addProperty("App::PropertyLink","uSource2")
		obj.addProperty("App::PropertyLink","vSource2")

		obj.addProperty("App::PropertyVector","Offset")
		obj.addProperty("App::PropertyVector","uOffset")
		obj.addProperty("App::PropertyVector","vOffset")
#		obj.addProperty("App::PropertyVector","vOffset")
#		obj.addProperty("App::PropertyInteger","start")
#		obj.addProperty("App::PropertyInteger","end")
		obj.addProperty("App::PropertyBool","borderMode")
		obj.addProperty("App::PropertyBool","onlyu")
		obj.addProperty("App::PropertyBool","onlyv")
		
		obj.addProperty("App::PropertyBool","uInverse")
		obj.addProperty("App::PropertyBool","u2Inverse")
		obj.addProperty("App::PropertyBool","vInverse")
		obj.addProperty("App::PropertyBool","v2Inverse")
		
		

	def execute(self,fp):
		self.createP(fp)

	def createP(self,fp):
		
		if fp.uSource2<>None and fp.vSource2<>None:
			
			ptsu= np.array(fp.uSource.Shape.Edge1.Curve.getPoles())
			ptsu2= np.array(fp.uSource2.Shape.Edge1.Curve.getPoles())
			ptsv= np.array(fp.vSource.Shape.Edge1.Curve.getPoles())
			ptsv2= np.array(fp.vSource2.Shape.Edge1.Curve.getPoles())
			
			if fp.uInverse:
				ptsu=np.array(ptsu)[::-1]
			if fp.u2Inverse:
				ptsu2=np.array(ptsu2)[::-1]

			if fp.vInverse:
				ptsv=np.array(ptsv)[::-1]

			if fp.v2Inverse:
				ptsv2=np.array(ptsv2)[::-1]


			
			
			sa=len(ptsu)
			sb=len(ptsv)
			pts=np.zeros(sa*sb*3).reshape(sa,sb,3)
			
			for u in range(sa):
				pts[u]=(ptsv*(sa-1-u)+ptsv2*(u))*1.0/(sa-1)

			poles=pts.copy()

			if 1:
				pts=pts.swapaxes(0,1)
				for v in range(sb):
					pts[v]=(ptsu*(sb-1-v)+ptsu2*(v))*1.0/(sb-1)

			poles += pts.swapaxes(0,1)

			for u in range(sa):
				for v in range(sb):
					pts[u,v] = ptsv[0]*(sa-1-u)*(sb-1-v)+ptsv[-1]*(u)*(sb-1-v) + ptsu[-1]*(sa-1-u)*(v)+ptsu2[-1]*(u)*(v)
					pts[u,v] *= 1.0/(sa-1)/(sb-1)

			poles -= pts.swapaxes(0,1)



			aecken=(sa-1)/3
			ya=[4]+[3]*(aecken-1)+[4]
			becken=(sb-1)/3
			yb=[4]+[3]*(becken-1)+[4]

			db=min(3,sb-1)
			if db==3:
				ya=[4]+[3]*(aecken-1)+[4]
			if db==2:
				ya=[3,3]
			if db==1:
				ya=[2,2]

			af=Part.BSplineSurface()
			af.buildFromPolesMultsKnots(poles, 
					ya,yb,
					range(len(ya)),range(len(yb)),
					False,False,db,3)

			fp.Shape=af.toShape()
			#Part.show(af.toShape())







			return

		sourceA=fp.uSource
		sourceB=fp.vSource


		ptsa=[p.Point for p in sourceA.Shape.Vertexes]
		sa=len(ptsa)
		if sa == 2:
			# assume curve
			print "curve u"
			ptsa= sourceA.Shape.Edge1.Curve.getPoles()

		sa=len(ptsa)

		if fp.uInverse:
			ptsa=np.array(ptsa)[::-1]
		else:
			ptsa=np.array(ptsa)


		ptsa=np.array(ptsa).reshape(sa,1,3)

		ptsb=[p.Point for p in sourceB.Shape.Vertexes]
		sb=len(ptsb)

		if sb == 2:
			# assume curve
			print "curve V"
			ptsb= sourceB.Shape.Edge1.Curve.getPoles()

		sb=len(ptsb)

		#richtung umschalten
		if fp.vInverse:
			ptsb=np.array(ptsb)[::-1]
		else:
			ptsb=np.array(ptsb)

		print ptsb[0]
		print ptsa[0]

		if 1: # startpunkte zusammenlagen # auf anfang von a
			ptsb += -ptsb[0] # + ptsa[0]

		sb=len(ptsb)
		
		print ptsb[0]
		endeb=ptsb[-1]
		startb=ptsb[0]

		ptsb2=ptsb.reshape(1,sb,3)


		if fp.uSource2<>None:
#			ptsbj=[p.Point for p in sourceB.Shape.Vertexes]
#			ptsa=np.array([p.Point for p in sourceA.Shape.Vertexes])


			ptsa=np.array(ptsa).reshape(sa,3)

			ptsa2=np.array([p.Point+ fp.uOffset  for p in fp.uSource2.Shape.Vertexes])

			sa2=len(ptsa2)
			print "sa2----------",sa2
			if sa2 == 2:
				# assume curve
				print "curve u-----------------------------------------"
				ptsa2= fp.uSource2.Shape.Edge1.Curve.getPoles()

			sa2=len(ptsa2)

			if fp.u2Inverse:
				ptsa2=np.array(ptsa2)[::-1]
			else:
				ptsa2=np.array(ptsa2)

			print "shape ptsa2 A ",ptsa2.shape

#			if 1: # startpunkte zusammenlegen
#				ptsa2 -= ptsa2[0] + +ptsa[0]+ ptsb[-1]

			print "shape ptsa2 B ",ptsa2.shape
			print "shape ptsa C ",ptsa.shape
			print ptsa[0]
			print ptsa2[0]
			print "--"

			ll=1.0*sb-1
			ptsaa=np.array([ptsa*(ll-i)/ll+ptsa2*i/ll  for i in range(sb)])

			for i in range(sb):
				t=ptsaa[i,0]
				ptsaa[i] += ptsb[i] -t 

			print "shape ptsa ",ptsa.shape

			ptsaa=np.array(ptsaa)
			ptsaa[:,:] += -ptsaa[0,0] + ptsa[0]


##		ptsa[:,0] += fp.Offset

			#ptsa=ptsa.swapaxes(0,1)

			if fp.borderMode:
				ptsa *= 0.5
				#ptsb[:,:,0:1] *= 0.5


		if 0 and fp.vSource2<>None:
			ptsb=[p.Point  for p in sourceB.Shape.Vertexes]
			sb=len(ptsb)
			ptsb=np.array(ptsb)
			
			ptsb2=[p.Point + fp.vOffset for p in fp.vSource2.Shape.Vertexes]
			ptsb2=np.array(ptsb2)

			print ("sa sb",sa,sb)
			ll=1.0*sa-1

			ptsbb=[ptsb*(ll-i)/ll+ptsb2*i/ll for i in range(sa)]

			ptsb=np.array(ptsbb)
			print "shape ptsbxx",ptsb.shape

			if fp.borderMode:
				ptsb *= 0.5
				#ptsb[:,:,0:1] *= 0.5



		#poles=ptsa+ptsb
		print "shape X ptsa",ptsa.shape
		print "shape X ptsb",ptsb.shape
		
		if fp.uSource2<>None:
			poles=np.array(ptsaa)
		else:
			poles=ptsa+ptsb2

		if fp.onlyu:
			poles=ptsa
		if fp.onlyv:
			poles=ptsb


		(a,b,c)=poles.shape
		print ("poles.shape a,b",a,b)

		aecken=(a-1)/3
		ya=[4]+[3]*(aecken-1)+[4]
		becken=(b-1)/3
		yb=[4]+[3]*(becken-1)+[4]

		db=min(3,a-1)
		if db==3:
			ya=[4]+[3]*(aecken-1)+[4]
		if db==2:
			ya=[3,3]
		if db==1:
			ya=[2,2]

		print ("a---",a,db,ya)
		af=Part.BSplineSurface()
		af.buildFromPolesMultsKnots(poles, 
				ya,yb,
				range(len(ya)),range(len(yb)),
				False,False,db,3)

		fp.Shape=af.toShape()
		#Part.show(af.toShape())





def createProduct():
	if 0:
		try:
			App.closeDocument("bering_testdaten")
		except:
			pass

		appdat=FreeCAD.ConfigGet('UserAppData')
		fn=appdat+'/FreeCAD_testfiles/bering_testdaten.fcstd'

		FreeCAD.open(fn)
		App.setActiveDocument("bering_testdaten")
		App.ActiveDocument=App.getDocument("bering_testdaten")
		Gui.ActiveDocument=Gui.getDocument("bering_testdaten")


	sf=App.ActiveDocument.addObject('Part::FeaturePython','ProductFace')
	Product(sf)
	ViewProvider(sf.ViewObject)
	sel=Gui.Selection.getSelection()
	sf.uSource=sel[0]
	sf.vSource=sel[1]
	if len(sel)>=3:	
		sf.uSource2=sel[2]
	if len(sel)>=4:	
		sf.vSource2=sel[3]

'''
	# alte Testfaelle
	sourceA=App.ActiveDocument.Sketch005
	sourceB=App.ActiveDocument.Sketch006
	_createP(sourceA,sourceB)
	r=App.ActiveDocument.ActiveObject

	sourceA=App.ActiveDocument.Sketch006
	sourceB=App.ActiveDocument.Sketch007
	_createP(sourceA,sourceB)
	r2=App.ActiveDocument.ActiveObject

	sourceA=App.ActiveDocument.Sketch007
	sourceB=App.ActiveDocument.Sketch005
	_createP(sourceA,sourceB)
	r3=App.ActiveDocument.ActiveObject
'''


def debugP(pts,label):


	print "debugP deaktiviert";return

	pts=[FreeCAD.Vector(p) for p in pts]
	obj=App.ActiveDocument.getObject(label)
	if obj == None:
		obj=App.ActiveDocument.addObject('Part::Feature',label)

	obj.Shape=Part.makePolygon([FreeCAD.Vector()]+pts)



class FaceConnection(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLink","aSource")
		obj.addProperty("App::PropertyLink","bSource")
		
#		obj.addProperty("App::PropertyVector","Offset")
#		obj.addProperty("App::PropertyVector","vOffset")
#		obj.addProperty("App::PropertyInteger","start")
#		obj.addProperty("App::PropertyInteger","end")
		obj.addProperty("App::PropertyBool","swapA")
		obj.addProperty("App::PropertyBool","swapB")
		obj.addProperty("App::PropertyBool","flipA")
		obj.addProperty("App::PropertyBool","flipB")

		obj.addProperty("App::PropertyBool","reverseA")
		obj.addProperty("App::PropertyBool","reverseB")
		obj.addProperty("App::PropertyBool","close")
		obj.addProperty("App::PropertyBool","mergeEdge")
		obj.addProperty("App::PropertyBool","displayConnect")
		obj.addProperty("App::PropertyEnumeration","mode").mode=['Connect','Seam']
		obj.addProperty("App::PropertyFloat","tangfacA").tangfacA=1
		obj.addProperty("App::PropertyFloat","tangfacB").tangfacB=1
		obj.addProperty("App::PropertyFloat","factor").factor=3

	def execute(self,fp):
		if fp.mode=='Seam':
			self.createSeam(fp)
		else:
			self.connect(fp)

	def createSeam(self,fp):
		print "in create seam ..."

		try:
			a=fp.aSource
			b=fp.bSource
		except:
			return
		sfa=a.Shape.Face1.Surface
		pa0=sfa.getPoles()

		sfb=b.Shape.Face1.Surface
		pb0=sfb.getPoles()

		print "shapes ..."
		print np.array(pa0).shape
		print np.array(pb0).shape

		if 1:

			if fp.swapA:
				pa=np.array(pa0).swapaxes(0,1)
			else:
				pa=np.array(pa0)
			if fp.swapB:
				pb=np.array(pb0).swapaxes(0,1)
			else:
				pb=np.array(pb0)

			if fp.reverseA:
				pa=pa[::-1]
			if fp.reverseB:
				pb=pb[::-1]

			debugP(pa[0],"pa_0")
			debugP(pb[1],"pb_1_x")
			debugP(pa[1],"pa_1_x")

			poles=np.array([pa[0],pa[0]+fp.tangfacA*(pa[0]-pa[1]),pb[0]+fp.tangfacB*(pb[0]-pb[1]),pb[0]]).swapaxes(0,1)

			af=Part.BSplineSurface()
			af.buildFromPolesMultsKnots(poles, 
				sfa.getUMultiplicities(),[4,4],
				sfa.getUKnots(),[0,1],
				False,False,sfa.UDegree,3)
			fp.Shape=af.toShape()

			if 0:
				sk=App.ActiveDocument.getObject(fp.Name+"_"+a.Name)
				if sk==None:
					sk=App.ActiveDocument.addObject('Part::Spline',fp.Name+"_"+a.Name)
					sk.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
				sk.Shape=af.toShape()
				sk.ViewObject.ControlPoints = True


			poles=np.concatenate([pa[::-1],[pa[0]+fp.tangfacA*(pa[0]-pa[1]),pb[0]+fp.tangfacB*(pb[0]-pb[1])],pb]).swapaxes(0,1)
			print "Concatt shape ",poles.shape
			(_a,_b,_c)=poles.shape

			ecken=(_b-4)/3
			ms=[4]+[3]*ecken+[4]

			af=Part.BSplineSurface()
			sfa.getUMultiplicities()
			af.buildFromPolesMultsKnots(poles, 
				sfa.getUMultiplicities(),ms,
				sfa.getUKnots(),range(len(ms)),
				False,False,sfa.UDegree,3)

			# return

			if fp.displayConnect:
				nn=fp.Name+"_"+a.Name+"_"+b.Name
				sk=App.ActiveDocument.getObject(nn)
				if sk==None:
					sk=App.ActiveDocument.addObject('Part::Spline',nn)
					sk.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
				sk.Shape=af.toShape()
				sk.ViewObject.ControlPoints = True







	def connect(self,fp):

		print "in connect ...."
		try:
			a=fp.aSource
			b=fp.bSource
		except:
			return
		mode='u0v0'
		sfa=a.Shape.Face1.Surface
		pa0=sfa.getPoles()

		sfb=b.Shape.Face1.Surface
		pb0=sfb.getPoles()

		if fp.flipB:
			pb1=np.array(pb0).swapaxes(0,1)
			pb2=pb1[::-1]
			pb0=np.array(pb2).swapaxes(0,1)

		if fp.flipA:
			pa1=np.array(pa0).swapaxes(0,1)
			pa2=pa1[::-1]
			pa0=np.array(pa2).swapaxes(0,1)



		print "shapes ..."
		print np.array(pa0).shape
		print np.array(pb0).shape

		tt=0.8
	#	tt=0.6
		tt=0.3
		tt=fp.factor*0.1

		shapes=[]

		mergeEdge=False
		mergeEdge=0


		if 1:

			if fp.swapA:
				pa=np.array(pa0).swapaxes(0,1)
			else:
				pa=np.array(pa0)
			if fp.swapB:
				pb=np.array(pb0).swapaxes(0,1)
			else:
				pb=np.array(pb0)

			if fp.reverseA:
				pa=pa[::-1]
			if fp.reverseB:
				pb=pb[::-1]

			debugP(pa[0],"pa_0")
			debugP(pb[1],"pb_1_x")
			debugP(pa[1],"pa_1_x")


			if fp.mergeEdge:
				pa[0]=pa[1]*tt+pb[1]*(1-tt)
				
			else:
				tb=pb[1]-pb[0]
				ta=pa[1]-pa[0]
				pa[1] = pa[0]+(ta-tb)

			debugP(pa[0],"pa_0_neu")
			debugP(pa[1],"pa_1_neu")


			if fp.close:

				#if mergeEdge:
#					pb[-1]=(pa[-2]+pb[-2])*0.5
				pa[-1]=(pa[-2]+pb[-2])*0.5
				#else:
				#	tb=pb[-2]-pb[-1]
				#	ta=pa[-2]-pa[-1]
				#	pa[-2] = pa[-1]+(ta-tb)



			if fp.swapA:
				poles=pa.swapaxes(0,1)
			else:
				poles=pa



		af=Part.BSplineSurface()
		af.buildFromPolesMultsKnots(poles, 
				sfa.getUMultiplicities(),sfa.getVMultiplicities(),
				sfa.getUKnots(),sfa.getVKnots(),
				False,False,sfa.UDegree,sfa.VDegree)

		sk=App.ActiveDocument.getObject(fp.Name+"_"+a.Name)
		if sk==None:
			sk=App.ActiveDocument.addObject('Part::Spline',fp.Name+"_"+a.Name)
			sk.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
		sk.Shape=af.toShape()
		# sk.ViewObject.ControlPoints = True
		sk.ViewObject.Visibility=False
		shapes += [af.toShape()]


		if 1:

			if fp.swapA:
				pa=np.array(pa0).swapaxes(0,1)
			else:
				pa=np.array(pa0)
			if fp.swapB:
				pb=np.array(pb0).swapaxes(0,1)
			else:
				pb=np.array(pb0)

			if fp.reverseA:
				pa=pa[::-1]
			if fp.reverseB:
				pb=pb[::-1]

			debugP(pb[0],"pb_0")
			debugP(pb[1],"pb_1")
			debugP(pa[1],"pa_1")

			if fp.mergeEdge:
				pb[0]=pa[1]*tt+pb[1]*(1-tt)
				## neu
#				tb=pb[1]-pb[0]
#				ta=pa[1]-pa[0]
#
#				pb[1] = pb[0]+(tb-ta)

			else:
				tb=pb[1]-pb[0]
				ta=pa[1]-pa[0]
				pb[1] = pb[0]+(tb-ta)



			if fp.close:
				#if mergeEdge:
				pb[-1]=(pa[-2]+pb[-2])*0.5
				#else:
				#	tb=pb[-2]-pb[-1]
				#	ta=pa[-2]-pa[-1]
				#	pb[-2] = pb[-1]+(tb-ta)

			debugP(pb[0],"pb_0_neu")
			debugP(pb[1],"pb_1_neu")


			if fp.swapB:
				poles=pb.swapaxes(0,1)
			else:
				poles=pb



		af=Part.BSplineSurface()
		af.buildFromPolesMultsKnots(poles, 
				sfb.getUMultiplicities(),sfb.getVMultiplicities(),
				sfb.getUKnots(),sfb.getVKnots(),
				False,False,sfb.UDegree,sfb.VDegree)

		sk=App.ActiveDocument.getObject(fp.Name+"_"+b.Name)
		if sk==None:
			sk=App.ActiveDocument.addObject('Part::Spline',fp.Name+"_"+b.Name)
			sk.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)

		sk.Shape=af.toShape()
		# sk.ViewObject.ControlPoints = True
		sk.ViewObject.Visibility=False
		
		shapes += [af.toShape()]

		fp.Shape=Part.Compound(shapes)


def createSeam():
	(fa,fb)=Gui.Selection.getSelection()

	sf=App.ActiveDocument.addObject('Part::FeaturePython','Seam')
	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	FaceConnection(sf)
	ViewProvider(sf.ViewObject)
	(us,vs)=Gui.Selection.getSelection()
	sf.aSource=fa
	sf.bSource=fb
	sf.mode='Seam'

	App.activeDocument().recompute()


def createDatumPlane():
	App.activeDocument().addObject('PartDesign::Plane','DatumPlane')

def createDatumLine():
	App.activeDocument().addObject('PartDesign::Line','DatumLine')

def begrid(bs,showTangents=True,showKnotCurves=True):

		comps=[]
		if showTangents:
			uks=bs.getUKnots()
			for i,k in enumerate(uks):
				comps  +=  [bs.uIso(k).toShape()] 

			vks=bs.getVKnots()
			for i,k in enumerate(vks):
				comps  +=  [bs.vIso(k).toShape()] 

		if showKnotCurves:
			poles=np.array(bs.getPoles())
			(uc,vc,_)=poles.shape
			nu=(uc-1)/3
			nv=(vc-1)/3
			tl=10
			for u in range(nu):
				for v in range(nv):
					try:
						comps += [Part.makePolygon([FreeCAD.Vector(poles[3*u,3*v]),FreeCAD.Vector(poles[3*u,3*v+1])])]
						comps += [Part.makePolygon([FreeCAD.Vector(poles[3*u,3*v]),FreeCAD.Vector(poles[3*u+1,3*v])])]
						if u>0:
							comps += [Part.makePolygon([FreeCAD.Vector(poles[3*u-1,3*v]),FreeCAD.Vector(poles[3*u,3*v])])]
						if v>0:
							comps += [Part.makePolygon([FreeCAD.Vector(poles[3*u,3*v-1]),FreeCAD.Vector(poles[3*u,3*v])])]
					except: pass
			for u in range(nu):
				try:
					v=vc-1
					comps += [Part.makePolygon([FreeCAD.Vector(poles[3*u,v]),FreeCAD.Vector(poles[3*u+1,v])])]
					comps += [Part.makePolygon([FreeCAD.Vector(poles[3*u,v-1]),FreeCAD.Vector(poles[3*u,v])])]
					if u>0:
						comps += [Part.makePolygon([FreeCAD.Vector(poles[3*u-1,v]),FreeCAD.Vector(poles[3*u,v])])]
				except:
					pass
			for v in range(nv):
				try:
					u=uc-1
					comps += [Part.makePolygon([FreeCAD.Vector(poles[u,3*v]),FreeCAD.Vector(poles[u,3*v+1])])]
					comps += [Part.makePolygon([FreeCAD.Vector(poles[u,3*v]),FreeCAD.Vector(poles[u-1,3*v])])]
					if v>0:
						comps += [Part.makePolygon([FreeCAD.Vector(poles[u,3*v]),FreeCAD.Vector(poles[u,3*v-1])])]
				except:
					pass
			try:
				u=uc-1
				v=vc-1
				comps += [Part.makePolygon([FreeCAD.Vector(poles[u,v]),FreeCAD.Vector(poles[u,v-1])])]
				comps += [Part.makePolygon([FreeCAD.Vector(poles[u,v]),FreeCAD.Vector(poles[u-1,v])])]
			except:
				pass

		return comps



class BeGrid(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLink","Source")
		obj.addProperty("App::PropertyBool","showTangents")
		obj.addProperty("App::PropertyBool","showKnotCurves")

		obj.showTangents=True
		obj.ViewObject.Selectable=False
		obj.ViewObject.LineWidth=1

	def execute(self,fp):
		comps=[]
		for f in fp.Source.Shape.Faces:
			bs=f.Surface
			showTangents=fp.showTangents
			showKnotCurves=fp.showKnotCurves
			compsf=begrid(bs,showTangents,showKnotCurves)
			comps +=compsf

		fp.ViewObject.LineColor=fp.Source.ViewObject.ShapeColor
		fp.ViewObject.PointColor=fp.Source.ViewObject.ShapeColor
		fp.Shape=Part.Compound(comps)

def createBeGrid():
	for  fa in Gui.Selection.getSelection():

		sf=App.ActiveDocument.addObject('Part::FeaturePython','BeGrid')
		sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
		BeGrid(sf)

		ViewProvider(sf.ViewObject)
		sf.Source=fa

		App.activeDocument().recompute()



def BSplineToBezierCurve():
	'''create a degree 3 curve with multiplicities always 3'''

	obj=Gui.Selection.getSelection()[0]
	bc=obj.Shape.Edge1.Curve

	if bc.Degree>3:
		nurbswb.say.showdialog("curves with degree >3 are not supported")
	bc.increaseDegree(3)

	mults=bc.getMultiplicities()
	knots=range(len(mults))

	bc2=Part.BSplineCurve()
	bc2.buildFromPolesMultsKnots(bc.getPoles(),	mults,knots,False,3)

	for i in range(1,len(mults)-1):
		print (i,mults[i])
		if mults[i]<3:
			bc2.insertKnot(i,3)

	t=App.ActiveDocument.addObject('Part::Spline',obj.Name)
	t.Label=obj.Label+" Bezier"
	t.Shape=bc2.toShape()
	t.ViewObject.ControlPoints=True

def BSplineToBezierCurve():
	'''create a degree 3 curve with multiplicities always 3'''


	for obj in Gui.Selection.getSelection():
		poles=[]
		for i,e in enumerate(obj.Shape.Edges):
			bc=e.Curve

			if bc.Degree>3:
				nurbswb.say.showdialog("curves with degree >3 are not supported")
			bc.increaseDegree(3)

			mults=bc.getMultiplicities()
			print mults
			pp=bc.getPoles()
			if i == 0:
				poles = bc.getPoles()
			if i == 1:
				print "in 1"
				if (poles[0]-pp[0]).Length<0.1 or (poles[0]-pp[-1]).Length<0.1:
					print "drehen"
					poles=poles[::-1]
				if (poles[-1]-pp[-1]).Length <0.1:
					print "drehen 2"
					pp=pp[::-1]
				poles += pp[1:]
			if i>1:
				if (poles[-1]-pp[-1]).Length <0.1:
					print "drehen 2"
					pp=pp[::-1]
				poles += pp[1:]


			pp=bc.getPoles()
#				print p
			print len(bc.getPoles())
			print pp[0]
			print pp[-1]

		Draft.makeWire(poles)
	#	return

		print len(poles)
		mults=[4]+[3]*((len(poles)-1)/3-1)+[4]
		knots=range(len(mults))
		print "huhu"
		print mults
		print knots

		bc2=Part.BSplineCurve()
		bc2.buildFromPolesMultsKnots(poles,	mults,knots,False,3)

		for i in range(1,len(mults)-1):
			print (i,mults[i])
			if mults[i]<3:
				bc2.insertKnot(i,3)

		t=App.ActiveDocument.addObject('Part::Spline',obj.Name)
		t.Label=obj.Label+" Bezier"
		t.Shape=bc2.toShape()
		t.ViewObject.ControlPoints=True
#---------------


class BezierSurface(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)

		obj.addProperty("App::PropertyLink","source")

		obj.addProperty("App::PropertyInteger","offset")
		obj.addProperty("App::PropertyInteger","level")
		obj.addProperty("App::PropertyBool","swap")
		obj.addProperty("App::PropertyBool","reverse")
		obj.addProperty("App::PropertyFloat","tangentFactor")

		obj.tangentFactor=1




	def execute(self,fp):

		bs=Part.BSplineSurface()
		sf=fp.source.Shape.Face1.Surface

		um=sf.getUMultiplicities()
		vm=sf.getVMultiplicities()


		umults=sf.getUMultiplicities()
		uknots=range(len(umults))

		vmults=sf.getVMultiplicities()
		vknots=range(len(vmults))

		bc2=Part.BSplineSurface()
		bc2.buildFromPolesMultsKnots(
			sf.getPoles(),
			umults,
			vmults,
			uknots,
			vknots,
			False,False,3,3
		)

		for i in range(1,len(umults)-1):
			print (i,umults[i])
			if umults[i]<3:
				bc2.insertUKnot(i,3,0)

		for i in range(1,len(vmults)-1):
			print (i,umults[i])
			if vmults[i]<3:
				bc2.insertVKnot(i,3,0)

		fp.Shape=bs.toShape()



#---------------



def BSplineToBezierSurface():

	s=Gui.Selection.getSelection()[0]
	sf=App.ActiveDocument.addObject('Part::FeaturePython','BezierSurface')

	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	BezierSurface(sf)
	ViewProvider(sf.ViewObject)
	sf.source=s
	App.activeDocument().recompute()





def SurfaceEditor():


	layout = '''
	MainWindow:
		QtGui.QLabel:
			setText:"***   Poles Editor   D E M O   ***"
		HorizontalGroup:
			setTitle: "Pole u v"
			QtGui.QLineEdit:
				id: 'ux'
				setText:"1"
				textChanged.connect: app.relativeMode
			QtGui.QLineEdit:
				id: 'vx'
				setText:"1"
				textChanged.connect: app.relativeMode

		HorizontalGroup:
			setTitle: "Position UV-tangential Normal"
			QtGui.QDial:
				id: 'udial'
				setFocusPolicy: QtCore.Qt.StrongFocus
				valueChanged.connect: app.relativeMode
				setMinimum: -100
				setMaximum: 100
			QtGui.QDial:
				id: 'vdial'
				setMinimum: -100
				setMaximum: 100
				valueChanged.connect: app.relativeMode
			QtGui.QDial:
				id: 'ndial'
				setMinimum: -100
				setMaximum: 100
				valueChanged.connect: app.relativeMode

		HorizontalGroup:
			setTitle: "Position XYZ"
			QtGui.QDial:
				id: 'xdial'
				setMinimum: -100
				setMaximum: 100
				setFocusPolicy: QtCore.Qt.StrongFocus
				valueChanged.connect: app.relativeMode
			QtGui.QDial:
				id: 'ydial'
				setMinimum: -100
				setMaximum: 100
				valueChanged.connect: app.relativeMode
			QtGui.QDial:
				id: 'zdial'
				setMinimum: -100.
				setMaximum: 100.
				valueChanged.connect: app.relativeMode

		HorizontalGroup:
			setTitle: "Rotation Euler"
			QtGui.QDial:
				id: 'xrot'
				setMinimum: -100
				setMaximum: 100
				setFocusPolicy: QtCore.Qt.StrongFocus
				valueChanged.connect: app.relativeMode
			QtGui.QDial:
				id: 'yrot'
				setMinimum: -100
				setMaximum: 100
				valueChanged.connect: app.relativeMode
			QtGui.QDial:
				id: 'zrot'
				setMinimum: -100.
				setMaximum: 100.
				valueChanged.connect: app.relativeMode

		HorizontalGroup:
			setTitle: "scale"
			QtGui.QSlider:
				id: 'scale'
				setValue: 10.0
				setOrientation: PySide.QtCore.Qt.Orientation.Horizontal
				valueChanged.connect: app.relativeMode

		QtGui.QCheckBox:
			id: 'showface'
			setText: 'Show Face'
			stateChanged.connect: app.relativeMode
			setChecked: True

		QtGui.QCheckBox:
			id: 'showtangents'
			setText: 'Show Tangents'
			stateChanged.connect: app.relativeMode
			setChecked: True

		QtGui.QCheckBox:
			id: 'showcurves'
			setText: 'Show Curves'
			stateChanged.connect: app.relativeMode
			setChecked: True



		HorizontalGroup:
			setTitle: "Mode"
			QtGui.QComboBox:
				id: 'mode'
				addItem: "u"
				addItem: "v"
#		QtGui.QPushButton:
#			setText: "Run Action"
#			clicked.connect: app.run

		QtGui.QPushButton:
			setText: "connect to selected point"
			clicked.connect: app.connectSelection


		QtGui.QPushButton:
			setText: "apply"
			clicked.connect: app.apply

		QtGui.QPushButton:
			setText: "apply and close"
			clicked.connect: app.applyandclose

		QtGui.QPushButton:
			setText: "cancel and close"
			clicked.connect: app.myclose

		setSpacer:
		'''

	def edit(u,v,s=10):

		print ("u,v,scale",u,v,s)
		#fp=App.ActiveDocument.Seam_ProductFace001
		
		App.activeDocument().recompute()



	class EditorApp(MikiApp):

		def resetDialog(self):
			for idx in  'udial','vdial','ndial','scale','xdial','ydial','zdial','xrot','yrot','zrot':
				if self.root.ids[idx].value()<>0:
					self.root.ids[idx].setValue(0)

		def connectSelection(self):

			fp=self.obj
			obj=App.ActiveDocument.getObject('temp_YY1')
			if obj == None:
				obj=App.ActiveDocument.addObject('Part::Spline','temp_YY1')
			bs=fp.Shape.Face1.Surface
			vec=Gui.Selection.getSelectionEx()[0].PickedPoints[0]

			upn=int(self.root.ids['ux'].text())
			vpn=int(self.root.ids['vx'].text())
			poles=bs.getPoles()

			uct,vct,_=np.array(poles).shape
			print ("XXXXXXXXXXXXXXXXXXXXXX   vec",vec)
			print(upn,vpn)

			center=poles[upn*3][vpn*3]
			poles=np.array(poles)

			center=poles[upn*3][vpn*3]
			poles=np.array(poles)

			startu=max(0,upn*3-1)
			endu=min(upn*3+2,uct)
			
			startv=max(0,vpn*3-1)
			endv=min(vpn*3+2,vct)
			print ("startu,endu",startu,endu)
			print ("startv,endv",startv,endv)


			ttp=poles[startu:endu,startv:endv] - center
			ttp += vec 
			
			poles[startu:endu,startv:endv]=ttp

			ss=Part.Sphere()
			ss.Radius=10
			s=ss.toShape()
			s.Placement.Base=poles[upn*3][vpn*3]

			bs2=Part.BSplineSurface()
			bs2.buildFromPolesMultsKnots(poles, 
				bs.getUMultiplicities(),
				bs.getVMultiplicities(),
				bs.getUKnots(),
				bs.getVKnots(),
				False,False,3,3)

			comps=begrid(bs2,
				self.root.ids['showcurves'].isChecked(),
				self.root.ids['showtangents'].isChecked()
				)



			if self.root.ids['showface'].isChecked():
				comps += [bs2.toShape()]
			self.Shape=bs2.toShape()
			# comps += [s]
			obj.Shape=Part.Compound(comps)
			#obj.Shape=Part.Compound(comps+ [s])

			#obj=App.ActiveDocument.addObject('Part::Spline','YY_'+fp.Name)
#			obj.Shape=bs.toShape()

			obj2=App.ActiveDocument.getObject('temp_YY2')
			
			if obj2 == None:
				obj2=App.ActiveDocument.addObject('Part::Spline','temp_YY2')
				obj2.ViewObject.ShapeColor=(1.0,0.,0.)
				obj2.ViewObject.LineColor=(0.3,0.3,1.)
				obj2.ViewObject.LineWidth=10

			self.NameObj2=obj2.Name

			comps=begrid(bs2,False,True)
			try:
				bs3=bs2.copy()
				bs3.segment(upn-1,upn+1,vpn-1,vpn+1)
			except:
				pass

			obj2.Shape=Part.Compound(comps+[s] + [bs3.toShape()])
			print "KUGELLLLLLLLLLLLLLLLL"
			print s


			App.activeDocument().recompute()

		def save(self):
			tt=time.time()
			try: obj=self.resultobj
			except:
				obj=App.ActiveDocument.addObject('Part::Spline','result')
				try:
					App.ActiveDocument.removeObject(self.NameObj2)
				except:
					pass
				try:
					App.ActiveDocument.removeObject(self.NameObj)
				except:
					pass
#			print "savet ",time.time()-tt

			tt=time.time()
			obj.ViewObject.hide()
			obj.Shape=self.Shape
			print "savetime hidden ",time.time()-tt
			tt=time.time()
			obj.ViewObject.show()
			obj.Shape=self.Shape
			print "savetime show ",time.time()-tt

			tt=time.time()
			z=self.Shape
			z=self.Shape
			print "savetime intern ",time.time()-tt

			self.obj=obj
			self.resultobj=obj
#			print "savetb ",time.time()-tt

		def applyandclose(self):
			fp=self.obj
			self.save()
	#		obj=App.ActiveDocument.getObject('YY_'+fp.Name)
			try:
				App.ActiveDocument.removeObject(self.NameObj2)
				App.ActiveDocument.removeObject(self.NameObj)
			except:
				pass
			self.close()


		def myclose(self):
			fp=self.obj
	#		self.save()
	#		obj=App.ActiveDocument.getObject('YY_'+fp.Name)
			try:
				App.ActiveDocument.removeObject(self.NameObj2)
				App.ActiveDocument.removeObject(self.NameObj)
			except:
				pass
			self.close()


		def run(self):
			print "run"
			edit(
				self.root.ids['udial'].value(),
				self.root.ids['vdial'].value(),
				self.root.ids['scale'].value(),
			)

		def relativeMode(self):
#			print "relative mode called"
			self.apply(False)

		def apply(self,save=True):
#			print "apply  implemented"
			st=time.time()
			try:
				fp=self.obj
			except: # not yet ready
				return
			print ("applay auf ",fp.Label)


			obj=App.ActiveDocument.getObject('temp_YY1')
			if obj == None:
				obj=App.ActiveDocument.addObject('Part::Spline','temp_YY1')
			bs=fp.Shape.Face1.Surface
			vec=FreeCAD.Vector(
						self.root.ids['xdial'].value()*self.root.ids['scale'].value(),
						self.root.ids['ydial'].value()*self.root.ids['scale'].value(),
						self.root.ids['zdial'].value()*self.root.ids['scale'].value()
						)

			try:
				upn=int(self.root.ids['ux'].text())
				vpn=int(self.root.ids['vx'].text())
			except:
				print "invalid input ux,vx"
				return

			poles=bs.getPoles()


			print "shape ",np.array(poles).shape
			uct,vct,_=np.array(poles).shape
			print ("vec",vec)
			print(upn,vpn)


			center=poles[upn*3][vpn*3]
			poles=np.array(poles)
			
			startu=max(0,upn*3-1)
			endu=min(upn*3+2,uct)
			
			startv=max(0,vpn*3-1)
			endv=min(vpn*3+2,vct)
			print ("startu,endu",startu,endu)
			print ("startv,endv",startv,endv)

#			if 0:
#				ttp=poles[upn*3-1:upn*3+2,vpn*3-1:vpn*3+2] - center
#				r#ot=FreeCAD.Rotation(self.root.ids['xrot'].value(),self.root.ids['yrot'].value(),self.root.ids['zrot'].value())

#				for u in 0,1,2:
#					for v in 0,1,2:
#						ttp[u,v]=rot.multVec(FreeCAD.Vector(ttp[u,v]))

#				(t1,t2)=bs.tangent(upn,vpn)
#				n=bs.normal(upn,vpn)
#				vectn=t1*self.root.ids['udial'].value()*self.root.ids['scale'].value()+\
#							t2*self.root.ids['vdial'].value()*self.root.ids['scale'].value()+\
#							n*self.root.ids['ndial'].value()*self.root.ids['scale'].value()


#				ttp += vec + center +vectn
#				poles[upn*3-1:upn*3+2,vpn*3-1:vpn*3+2]=ttp

			if 1 :
				ttp=poles[startu:endu,startv:endv] - center
				rot=FreeCAD.Rotation(self.root.ids['xrot'].value(),self.root.ids['yrot'].value(),self.root.ids['zrot'].value())

				for u in range(0,endu-startu):
					for v in range(0,endv-startv):
						ttp[u,v]=rot.multVec(FreeCAD.Vector(ttp[u,v]))

				(t1,t2)=bs.tangent(upn,vpn)
				n=bs.normal(upn,vpn)
				vectn=t1*self.root.ids['udial'].value()*self.root.ids['scale'].value()+\
							t2*self.root.ids['vdial'].value()*self.root.ids['scale'].value()+\
							n*self.root.ids['ndial'].value()*self.root.ids['scale'].value()


				ttp += vec + center +vectn
				poles[startu:endu,startv:endv]=ttp




			ss=Part.Sphere()
			ss.Radius=10
			s=ss.toShape()
			s.Placement.Base=poles[upn*3][vpn*3]

			print "Time A",time.time()-st
			
			bs2=Part.BSplineSurface()
			bs2.buildFromPolesMultsKnots(poles, 
				bs.getUMultiplicities(),
				bs.getVMultiplicities(),
				bs.getUKnots(),
				bs.getVKnots(),
				False,False,3,3)

			comps=begrid(bs2,
				self.root.ids['showcurves'].isChecked(),
				self.root.ids['showtangents'].isChecked()
				)


			print "Time B1 ",time.time()-st
			if self.root.ids['showface'].isChecked():
				comps += [bs2.toShape()]


			self.Shape=bs2.toShape()
			if not save:
				print "Time B2 ",time.time()-st
				#comps += [s]
				obj.Shape=Part.Compound(comps)
				#obj.Shape=Part.Compound(comps+ [s])
				print "Time B2a ",time.time()-st
				#obj=App.ActiveDocument.addObject('Part::Spline','YY_'+fp.Name)
	#			obj.Shape=bs.toShape()

				obj2=App.ActiveDocument.getObject('temp_YY2')
				
				if obj2 == None:
					obj2=App.ActiveDocument.addObject('Part::Spline','temp_YY2')
					obj2.ViewObject.ShapeColor=(1.0,0.,0.)
					obj2.ViewObject.LineColor=(0.3,0.3,1.)
					obj2.ViewObject.LineWidth=10

				self.NameObj2=obj2.Name

				print "Time B3 ",time.time()-st
				comps=begrid(bs2,False,True)
				bs3=bs2.copy()
				print "frames"
				print (startu,endu-1,startv,endv-1)
				print bs3.getUKnots()
				print bs3.getVKnots()
				try:
					bs3.segment(startu,endu-1,startv,endv-1)
					print "Time B4 ",time.time()-st
					obj2.Shape=Part.Compound(comps+[s] + [bs3.toShape()])
					print "Time B ",time.time()-st
				except:
					obj2.Shape=Part.Compound(comps+[s])
					pass

			if save:
				print "SAVE"
				sts=time.time()
				self.save()
				print "Time SCA ",time.time()-sts
				sts=time.time()
				self.apply(False)
				print "Time SCB ",time.time()-sts
				sts=time.time()
				self.resetDialog()
				print "Time SCC ",time.time()-sts

			App.activeDocument().recompute()
			print "Time C ",time.time()-st



	fp=Gui.Selection.getSelection()[0]

	obj=App.ActiveDocument.getObject('YY_'+fp.Name)
	if obj == None:
		obj=App.ActiveDocument.addObject('Part::Spline','temp_YY1')
	obj.Shape=fp.Shape

	mikigui = createMikiGui2(layout, EditorApp)
	print mikigui
	mikigui.obj=fp
	mikigui.NameObj=obj.Name
	mikigui.relativeMode()





def addKnot():


	layout = '''
	MainWindow:
		QtGui.QLabel:
			setText:"***   Dock Widget    D E M O   ***"

		HorizontalGroup:
			setTitle: "Position UV-tangential Normal"
			QtGui.QDial:
				id: 'udial'
				setFocusPolicy: QtCore.Qt.StrongFocus
				valueChanged.connect: app.displayKnot
				setMinimum: -100
				setMaximum: 100
			QtGui.QDial:
				id: 'vdial'
				setMinimum: -100
				setMaximum: 100
				valueChanged.connect: app.displayKnot

		HorizontalGroup:
			setTitle: "Direction"
			QtGui.QComboBox:
				id: 'mode'
				addItem: "u"
				addItem: "v"
#		QtGui.QPushButton:
#			setText: "Run Action"
#			clicked.connect: app.run
		QtGui.QPushButton:
			setText: "add Knot"
			clicked.connect: app.addKnot

		QtGui.QPushButton:
			setText: "close"
			clicked.connect: app.myclose
		setSpacer:
		'''





	class BeKnotApp(MikiApp):

		def run(self):
			print "run"
			insertKnot(
				self.root.ids['pos'].text(),
				self.root.ids['mode'].currentText(),
			)

		def myclose(self):
			try:
				App.ActiveDocument.removeObject(self.NameObj)
			except: 
				pass
			self.close()



		def displayKnot(self):
			mode=str(self.root.ids['mode'].currentText())
			uval=self.root.ids['udial'].value()
			vval=self.root.ids['vdial'].value()

			fp=Gui.Selection.getSelection()[0]
			bs=fp.Shape.Face1.Surface
#			print ("Mode",mode)
			if mode=='u':
				knots=bs.getUKnots()
#				print knots
				c1=bs.uIso((knots[-1]-knots[0])*((uval-0.5)+100.)/200.)
				c2=bs.uIso((knots[-1]-knots[0])*((uval+0.5)+100.)/200.)
			if mode=='v':
				knots=bs.getVKnots()
#				print knots
				c1=bs.vIso((knots[-1]-knots[0])*((vval-0.5)+100.)/200.)
				c2=bs.vIso((knots[-1]-knots[0])*((vval+0.5)+100.)/200.)


			comps=begrid(bs,True,False)

			self.NameObj='Kp_'+fp.Name
			obj=App.ActiveDocument.getObject(self.NameObj)
			if obj == None:
				obj=App.ActiveDocument.addObject('Part::Spline',self.NameObj)

			obj.Shape=Part.Compound(comps+[c1.toShape(),c2.toShape()])

		def addKnot(self):
			mode=str(self.root.ids['mode'].currentText())
			uval=self.root.ids['udial'].value()
			vval=self.root.ids['vdial'].value()
			
			fp=Gui.Selection.getSelection()[0]
			bs=fp.Shape.Face1.Surface
#			print ("Mode",mode)
			if mode=='u':
				knots=bs.getUKnots()
#				print knots
				pos=(knots[-1]-knots[0])*(uval+100.)/200.
				bs.insertUKnot(pos,3,0)
			if mode=='v':
				knots=bs.getVKnots()
#				print knots
				pos=(knots[-1]-knots[0])*(vval+100.)/200.
				bs.insertVKnot(pos,3,0)

			obj=App.ActiveDocument.addObject('Part::Spline','result')
			
			umults=bs.getUMultiplicities()
			uknots=range(len(umults))

			vmults=bs.getVMultiplicities()
			vknots=range(len(vmults))

			bs2=Part.BSplineSurface()
			bs2.buildFromPolesMultsKnots(

				bs.getPoles(),
				umults,
				vmults,
				uknots,
				vknots,
				False,False,3,3
			)


			
			
			obj.Shape=bs2.toShape()
			App.activeDocument().recompute()

			App.ActiveDocument.removeObject(self.NameObj)

			fp.ViewObject.hide()
			Gui.Selection.clearSelection()
			Gui.Selection.addSelection(obj)
			
			self.displayKnot()
#			obj=App.ActiveDocument.getObject('Kp_'+fp.Name)
#			if obj == None:
#				obj=App.ActiveDocument.addObject('Part::Spline','Kp_'+fp.Name)
#			obj.Shape=c.toShape()





	mikigui = createMikiGui2(layout, BeKnotApp)
	mikigui.displayKnot()
	




def connectFaces():
	(fa,fb)=Gui.Selection.getSelection()
#	(b2,b3)=_connectFaces(b,r3,mode='v0v0')

	sf=App.ActiveDocument.addObject('Part::FeaturePython','FaceConnection')
	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	FaceConnection(sf)
	ViewProvider(sf.ViewObject)
	(us,vs)=Gui.Selection.getSelection()
	sf.aSource=fa
	sf.bSource=fb
	#sf.swapB=True
	#sf.close=True

	App.activeDocument().recompute()

	return



	(b,b1)=_connectFaces(r,r2,mode='u0v0')
	#_connectFaces(r3,rr,mode='v0v0')
	(b2,b3)=_connectFaces(b,r3,mode='v0v0')
	(b4,b5)=_connectFaces(b3,b1,mode='v0v0')
#	_connectFaces(



def fixCorner():


	(a,b,c)=Gui.Selection.getSelection()
	_fixCorner(a,b,c)
	App.activeDocument().recompute()






class BePlane(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyInteger","uSegments")
		obj.addProperty("App::PropertyInteger","vSegments")
		obj.addProperty("App::PropertyBool","swap")
		obj.addProperty("App::PropertyBool","reverse")
		obj.addProperty("App::PropertyFloat","uSize")
		obj.addProperty("App::PropertyFloat","vSize")
		obj.addProperty("App::PropertyFloat","zSize")
		obj.addProperty("App::PropertyFloat","noise")

		obj.uSegments=4
		obj.vSegments=3
		obj.uSize=1000
		obj.vSize=800
		obj.zSize=500

	def execute(self,fp):
		uc=fp.uSegments*3+1
		vc=fp.vSegments*3+1
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)*fp.noise
		poles *= fp.zSize
		for u in range(uc):
			poles[u,:,0]=fp.uSize*u
		for v in range(vc):
			poles[:,v,1]=fp.vSize*v
		
		um=[4]+[3]*(fp.uSegments-1)+[4]
		vm=[4]+[3]*(fp.vSegments-1)+[4]
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(
			poles,
			um,vm,
			range(len(um)),range(len(vm)),
			False,False,3,3)
		fp.Shape=bs.toShape()

		sf=bs
		print (sf.getUMultiplicities(),sf.getVMultiplicities(),sf.getUKnots(),sf.getVKnots(),)
		print poles.shape


	def execute(self,fp):
		uc=3+fp.uSegments
		vc=3+fp.vSegments
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)*fp.noise
		poles *= fp.zSize
		for u in range(uc):
			poles[u,:,0]=fp.uSize*u
		for v in range(vc):
			poles[:,v,1]=fp.vSize*v

		if 0:
			poles[0,:,2]=0
			poles[-1,:,2]=0
			poles[:,0,2]=0
			poles[:,-1,2]=0
		
		um=[4]+[1]*(fp.uSegments-1)+[4]
		vm=[4]+[1]*(fp.vSegments-1)+[4]
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(
			poles,
			um,vm,
			range(len(um)),range(len(vm)),
			False,False,3,3)
		fp.Shape=bs.toShape()

		for i in range(1,fp.uSegments):
			bs.insertUKnot(i,3,0)
		for i in range(1,fp.vSegments):
			bs.insertVKnot(i,3,0)

		sf=bs
		print (sf.getUMultiplicities(),sf.getVMultiplicities(),sf.getUKnots(),sf.getVKnots(),)
		print poles.shape





def createBePlane():
	sf=App.ActiveDocument.addObject('Part::FeaturePython','BePlane')
	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	BePlane(sf)
	ViewProvider(sf.ViewObject)


class BeTube(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyInteger","uSegments")
		obj.addProperty("App::PropertyInteger","vSegments")
		obj.addProperty("App::PropertyInteger","offset")
		obj.addProperty("App::PropertyBool","swap")
		obj.addProperty("App::PropertyBool","reverse")
		obj.addProperty("App::PropertyFloat","uSize")
		obj.addProperty("App::PropertyFloat","vSize")
		obj.addProperty("App::PropertyFloat","noise")

		obj.uSegments=5
		obj.vSegments=3
		obj.uSize=1000
		obj.vSize=200


	# offen form
	def execute(self,fp):
		uc=fp.uSegments*3+1
		vc=fp.vSegments*3+1
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)
		poles *=200 +500
		for u in range(uc):
			poles[u,:,0]=fp.uSize*np.cos(2*u*np.pi/uc)
			poles[u,:,1]=fp.uSize*np.sin(2*u*np.pi/uc)
		for v in range(vc):
			poles[:,v,2]=fp.vSize*v

		print poles

		um=[4]+[3]*(fp.uSegments-1)+[4]
		vm=[4]+[3]*(fp.vSegments-1)+[4]
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(
			poles,
			um,vm,
			range(len(um)),range(len(vm)),
			False,False,3,3)

		for i in range(0,fp.uSegments):
			bs.insertUKnot(i,3,0)
		for i in range(1,fp.vSegments):
			bs.insertVKnot(i,3,0)

		fp.Shape=bs.toShape()

	def execute(self,fp):
		uc=3+fp.uSegments
		vc=3+fp.vSegments
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)*fp.noise

		for u in range(uc):
			poles[u,:,0]+= fp.uSize*np.cos(2*u*np.pi/(uc-1))
			poles[u,:,1]+= fp.uSize*np.sin(2*u*np.pi/(uc-1))

		poles[-1]=poles[0]
		poles[-2]=2*poles[0]-poles[1]

		for v in range(vc):
			poles[:,v,2]=fp.vSize*v

		if 0:
			poles[0,:,2]=0
			poles[-1,:,2]=0
			poles[:,0,2]=0
			poles[:,-1,2]=0
		
		um=[4]+[1]*(fp.uSegments-1)+[4]
		vm=[4]+[1]*(fp.vSegments-1)+[4]
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(
			poles,
			um,vm,
			range(len(um)),range(len(vm)),
			False,False,3,3)
		fp.Shape=bs.toShape()

		for i in range(1,fp.uSegments):
			bs.insertUKnot(i,3,0)
		for i in range(1,fp.vSegments):
			bs.insertVKnot(i,3,0)

		sf=bs
		print (sf.getUMultiplicities(),sf.getVMultiplicities(),sf.getUKnots(),sf.getVKnots(),)
		print poles.shape




	def Xexecute(self,fp): # gehts
		uc=fp.uSegments*3+3
		vc=fp.vSegments*3+1
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)
		poles *=200 +500
		for u in range(uc):
			poles[u,:,0]=fp.uSize*np.cos(2*u*np.pi/uc)
			poles[u,:,1]=fp.uSize*np.sin(2*u*np.pi/uc)
		for v in range(vc):
			poles[:,v,2]=fp.vSize*v

		um=[3]+[3]*(fp.uSegments)+[3]
		vm=[4]+[3]*(fp.vSegments-1)+[4]
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(
			poles,
			um,vm,
			range(len(um)),range(len(vm)),
			True,False,3,3)



		fp.Shape=bs.toShape()

	def Xexecute(self,fp):
		uc=fp.uSegments+3
		vc=fp.vSegments+3
		poles=np.random.random(uc*vc*3).reshape(uc,vc,3)
		poles *= fp.noise
		for u in range(uc):
			poles[u,:,0] += fp.uSize*np.cos(2*u*np.pi/uc)
			poles[u,:,1] += fp.uSize*np.sin(2*u*np.pi/uc)
		for v in range(vc):
			poles[:,v,2] += fp.vSize*v

		um=[1]*(fp.uSegments+4)
		vm=[4]+[1]*(fp.vSegments-1)+[4]

		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(
			poles,
			um,vm,
			range(len(um)),range(len(vm)),
			True,False,3,3)

		for i in range(0,fp.uSegments+3):
			bs.insertUKnot(i,3,0)
		for i in range(1,fp.vSegments):
			bs.insertVKnot(i,3,0)

		fp.Shape=bs.toShape()







def createBeTube():
	sf=App.ActiveDocument.addObject('Part::FeaturePython','BeTube')
	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	BeTube(sf)
	ViewProvider(sf.ViewObject)


class BePlaneTubeConnector(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)

		obj.addProperty("App::PropertyLink","plane")
		obj.addProperty("App::PropertyLink","tube")

		obj.addProperty("App::PropertyInteger","offset")
		obj.addProperty("App::PropertyInteger","level")
		obj.addProperty("App::PropertyBool","swap")
		obj.addProperty("App::PropertyBool","reverse")
		obj.addProperty("App::PropertyFloat","tangentFactor")

		obj.tangentFactor=1




	def execute(self,fp):
		sf=fp.plane.Shape.Face1.Surface
		poles=np.array(sf.getPoles())
		sfr=fp.tube.Shape.Face1.Surface
		polesr=np.array(sfr.getPoles())
		polesr=np.concatenate([polesr,polesr])
		a=poles.shape[0]

		print polesr.shape
		k2=fp.tangentFactor
		level=fp.level*3
		offset=fp.offset*3
		if fp.swap:
			if fp.reverse:
				poles[0:a,-1] =polesr[0+offset:a+offset,level]
				poles[0:a,-2] = (1+k2)*polesr[0+offset:a+offset,level]-k2*polesr[0+offset:a+offset,level+1]
			else:
				poles[0:a,-1] =polesr[0+offset:a+offset,level][::-1]
				poles[0:a,-2] = (1+k2)*polesr[0+offset:a+offset,level][::-1]-k2*polesr[0+offset:a+offset,level+1][::-1]
		else:
			if fp.reverse:
				poles[0:a,0] =polesr[0+offset:a+offset,level]
				poles[0:a,1] = (1+k2)*polesr[0+offset:a+offset,level]-k2*polesr[0+offset:a+offset,level+1]
			else:
				poles[0:a,0] =polesr[0+offset:a+offset,level][::-1]
				poles[0:a,1] = (1+k2)*polesr[0+offset:a+offset,level][::-1]-k2*polesr[0+offset:a+offset,level+1][::-1]


		bs=Part.BSplineSurface()

		um=sf.getUMultiplicities()
		vm=sf.getVMultiplicities()
		bs.buildFromPolesMultsKnots(
				poles,
				um,vm,
				range(len(um)),range(len(vm)),
				False,False,3,3)
		fp.Shape=bs.toShape()



def createPlaneTubeConnector():
	sf=App.ActiveDocument.addObject('Part::FeaturePython','BeConnector')
	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	BePlaneTubeConnector(sf)
	(sf.plane,sf.tube)=Gui.Selection.getSelection()
	ViewProvider(sf.ViewObject)






class HelmetTubeConnector(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLink","helmet")
		obj.addProperty("App::PropertyLink","tube")

		obj.addProperty("App::PropertyInteger","offset")
		obj.addProperty("App::PropertyInteger","level")
		obj.addProperty("App::PropertyBool","swap")
		obj.addProperty("App::PropertyBool","reverse")
		obj.addProperty("App::PropertyFloat","tangentFactorTube")
		obj.addProperty("App::PropertyFloat","tangentFactorHelmet")

		obj.tangentFactorTube=1
		obj.tangentFactorHelmet=1



	def execute(self,fp):

		sf=fp.helmet.Shape.Face1.Surface
		poles=np.array(sf.getPoles())
		a=poles

		ring=np.concatenate([
			a[:-1,0],
			a[-1,:-1],
			a[1:,-1][::-1],
			a[0,1:][::-1]
			])

		ring2=np.concatenate([
			[a[1,1]],
			a[1:-2,1],
			[a[-2,1]],[a[-2,1]],
			a[-2,1:-2],
			[a[-2,-2]],[a[-2,-2]],
			a[2:-1,-2][::-1],
			[a[1,-2]],[a[1,-2]],
			a[1,2:-1][::-1],
			[a[1,1]]
			
			])


		k1=fp.tangentFactorHelmet
		ring2a=(1+k1)*ring-k1*ring2
		ring2=ring2a


		tube=fp.tube
		tsf=tube.Shape.Face1.Surface
		tps=np.array(tsf.getPoles()).swapaxes(0,1)
		k2=fp.tangentFactorTube

		if fp.swap:
			ring4=tps[fp.level]
			ring3=(1+k2)*tps[fp.level]-k2*tps[1+fp.level]
		else:
			ring4=tps[-1-fp.level]
			ring3=(1+k2)*tps[-1-fp.level]-k2*tps[-2-fp.level]

		if fp.reverse:
			offset=fp.offset*3+1
		else:
			offset=fp.offset*3

		ring3a=np.concatenate([ring3[offset:],ring3[:offset]])
		ring4a=np.concatenate([ring4[offset:],ring4[:offset]])

		if fp.reverse:
			ring3,ring4=ring3a[::-1],ring4a[::-1]
		else:
			ring3,ring4=ring3a,ring4a


		bs=Part.BSplineSurface()
		print np.array([ring,ring2,ring3,ring4]).shape

		bs.buildFromPolesMultsKnots([ring,ring2,ring3,ring4],
			[4,4],[3,3,3,3,3,3,3,3,3],
			[0,1],range(9),
			False,True,3,3)

		fp.Shape=bs.toShape()



def createHelmet():
	import nurbswb.helmet
	reload(nurbswb.helmet)
	nurbswb.helmet.createHelmet()

def createHelmetTubeConnector():
	sf=App.ActiveDocument.addObject('Part::FeaturePython','BeConnector')
	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	HelmetTubeConnector(sf)
	(sf.helmet,sf.tube)=Gui.Selection.getSelection()
	ViewProvider(sf.ViewObject)



class BeTriangle(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLink","curveA")
		obj.addProperty("App::PropertyLink","curveB")
		obj.addProperty("App::PropertyLink","curveC")

		obj.addProperty("App::PropertyString","edgeA")
		obj.addProperty("App::PropertyString","edgeB")
		obj.addProperty("App::PropertyString","edgeC")

		obj.addProperty("App::PropertyInteger","offset")
		obj.addProperty("App::PropertyInteger","level")
		obj.addProperty("App::PropertyBool","swap")
		obj.addProperty("App::PropertyBool","reverse")
#		obj.addProperty("App::PropertyFloat","tangentFactorTube")
#		obj.addProperty("App::PropertyFloat","tangentFactorHelmet")

#		obj.tangentFactorTube=1
#		obj.tangentFactorHelmet=1

		obj.edgeC="Edge1"
		obj.edgeA="Edge1"


	def execute(self,fp):

		#zusammensetzung
		spa=[[-100,0,0],[-80,20,0],[-20,80,0],[0,100,0]]
		spb=[[0,100,0],[20,80,0],[80,20,0],[100,0,0]]
		spc=[[-100,0,0],[-80,0,0],[-20,0,-20],[0,0,-20],[20,0,-20],[80,0,0],[100,0,0]]

		if fp.edgeA=='':
			spa=[v.Point for v in fp.curveA.Shape.Vertexes]
		else:
			edge=getattr(fp.curveA.Shape,fp.edgeA)
			try:
				spa=edge.Curve.getPoles()
			except: 
				print "no Vertexes"
				try:
					spa=[v.Point for v in edge.Vertexes]
				except:
					print "no poles"
					return

#		spb=[v.Point for v in fp.curveB.Shape.Vertexes]

		if fp.edgeB=='':
			spb=[v.Point for v in fp.curveB.Shape.Vertexes]
		else:
			edge=getattr(fp.curveB.Shape,fp.edgeB)
			try:
				spb=edge.Curve.getPoles()
			except: 
				print "no Vertexes"
				try:
					spb=[v.Point for v in edge.Vertexes]
				except:
					print "no poles"
					return

		if fp.edgeC=='':
			spc=[v.Point for v in fp.curveC.Shape.Vertexes]
		else:
			edge=getattr(fp.curveC.Shape,fp.edgeC)
			try:
				spc=edge.Curve.getPoles()
			except: 
				print "no Vertexes"
				try:
					spc=[v.Point for v in edge.Vertexes]
				except:
					print "no poles"
					return
		print "ha----------------------------ha"


		
		if (spa[-1]-spb[-1]).Length<0.01:
			spb=spb[::-1]
		if (spa[0]-spb[-1]).Length<0.01:
			spb=spb[::-1]
			spa=spa[::-1]
		if (spa[0]-spb[0]).Length<0.01:
			spa=spa[::-1]
		if (spc[-1]-spa[0]).Length<0.01:
			spc=spc[::-1]
		if (spc[0]-spb[-1]).Length<0.01:
			spc=spc[::-1]


		print "--spa--"
		print spa
		print "--spb-----"
		print spb
		print "--spc-----"
		print spc
		assert (spa[-1]-spb[0]).Length<0.01
		assert (spb[-1]-spc[-1]).Length<0.01
		assert (spc[0]-spa[0]).Length<0.01


		rings=np.zeros(4*4*3).reshape(4,4,3)
		rings[0]=spa
		rings[-1]=spc[3:]
		rings[:,-1]=spb
		rings[:,0]=spc[0:4]
		for i in 1,2:
			for j in 1,2:
				rings[i,j]=(2+rings[i,0]+rings[i,-1]+2*rings[0,j]+rings[-1,j])/6 +30

		rr=np.array(rings)


		rcc=rings[-1][::-1]

		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(rr,
			[4,4],[4,4],
			[0,2],[0,2],
			False,False,3,3)
		if 0:
			bs.insertUKnot(1,3,0)
			bs.insertVKnot(1,3,0)
			bs.insertVKnot(1.5,3,0)
			bs.insertUKnot(1.5,3,0)

		bs2=Part.BSplineSurface()
		um=bs.getUMultiplicities()
		vm=bs.getVMultiplicities()
		bs2.buildFromPolesMultsKnots(bs.getPoles(),
			um,vm,range(len(um)),range(len(vm)),
			False,False,3,3)
		bs=bs2



		fp.Shape=bs.toShape()

		return
		# ab hier tangentsspiele todo!!

#--------------------------------
		rA=np.array([rr[0],rr[0]+[-30,30,30]])
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(rA,
			[2,2],[4,4],
			[0,2],[0,2],
			False,False,1,3)
		sk=App.ActiveDocument.addObject('Part::Spline','rA')
		sk.Shape=bs.toShape()

	#	rr[1]=rr[0]+rA[0]-rA[1]

		rrs=rr.swapaxes(0,1)
		
		rcc2=rrs[0][::-1]

		ptsa=[FreeCAD.Vector(p) for  p in rcc[:-1]]
		ptsa += [FreeCAD.Vector(p) for  p in rcc2]
		ptsb=[p+ FreeCAD.Vector(0,-30,0) for p in ptsa]
		# Draft.makeWire(ptsa)
		for p in ptsa:
			print p 
		
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots([ptsa,ptsb],
			[2,2],[4,3,4],
			[0,2],[0,1,2],
			False,False,1,3)
		sk=App.ActiveDocument.addObject('Part::Spline','rC')
		sk.Shape=bs.toShape()
		


		rB=np.array([rrs[-1],rrs[-1]+[30,30,20]])
		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(rB,
			[2,2],[4,4],
			[0,2],[0,2],
			False,False,1,3)
		sk=App.ActiveDocument.addObject('Part::Spline','rB')
		sk.Shape=bs.toShape()

		#rrs[-2][2:]=rrs[-1][2:]+rB[0][2:]-rB[1][2:]
		rrs[-2][1:]=rrs[-1][1:]+rB[0][1:]-rB[1][1:]

		rru=rrs.swapaxes(0,1)
		#rru=rings
		#rru=rr





		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(rru,
			[4,4],[4,4],
			[0,2],[0,2],
			False,False,3,3)
		if 0:
			bs.insertUKnot(1,3,0)
			bs.insertVKnot(1,3,0)

			bs.insertUKnot(1.5,3,0)



def createTriangle():
	'''createTriangle: creates a BSpline Surface for an area of 3 selected and connected curves
	at the moment the curves must have 4,4,7 poles 
	the long side should have multiplicities 4,3,4
	
	'''
	sf=App.ActiveDocument.addObject('Part::FeaturePython','BeTriangle')
	sf.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	BeTriangle(sf)
	(sf.curveA,sf.curveB,sf.curveC)=Gui.Selection.getSelection()
	ViewProvider(sf.ViewObject)


def SplitIntoCells():
	'''split a BSpline Face into segment cells'''

	obj=Gui.Selection.getSelection()[0]
	f=obj.Shape.Face1
	bs=f.Surface
	luks=len(bs.getUKnots())
	lvks=len(bs.getVKnots())

	uks=bs.getUKnots()
	vks=bs.getVKnots()

	comps=[]
	for ui in range(0,luks-1):
		for vi in range(0,lvks-1):
			bsa=bs.copy()
			bsa.segment(uks[ui],uks[ui+1],vks[vi],vks[vi+1])
			comps +=[bsa.toShape()]


	sk=App.ActiveDocument.addObject('Part::Spline','split')
	sk.Shape=Part.Compound(comps)



def createTangentStripes():

	obj=Gui.Selection.getSelection()[0]
	f=obj.Shape.Face1
	bs=f.Surface
	luks=len(bs.getUKnots())
	lvks=len(bs.getVKnots())

	uks=bs.getUKnots()
	vks=bs.getVKnots()

	comps=[]
	stripes=[
		[0,1],
		[-2,-1]
	]
	poles=np.array(bs.getPoles())
	for a,b in stripes:
		rb=[poles[a],poles[b]]
		bs2=Part.BSplineSurface()
		bs2.buildFromPolesMultsKnots(rb,
			[2,2],bs.getVMultiplicities(),
			[0,2],bs.getVKnots(),
			False,False,1,3)

		sk=App.ActiveDocument.addObject('Part::Spline','split')
		sk.Shape=bs2.toShape()

	poles=np.array(poles).swapaxes(0,1)

	for a,b in stripes:
		rb=[poles[a],poles[b]]
		bs2=Part.BSplineSurface()
		bs2.buildFromPolesMultsKnots(rb,
			[2,2],bs.getUMultiplicities(),
			[0,2],bs.getUKnots(),
			False,False,1,3)

		sk=App.ActiveDocument.addObject('Part::Spline','split')
		sk.Shape=bs2.toShape()

#-----------------



class Cell(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyLink","source")
		obj.addProperty("App::PropertyLink","curveB")
		obj.addProperty("App::PropertyLink","curveC")

#		obj.addProperty("App::PropertyString","edgeA")
#		obj.addProperty("App::PropertyString","edgeB")
#		obj.addProperty("App::PropertyString","edgeC")

		obj.addProperty("App::PropertyInteger","uBegin").uBegin=0
		obj.addProperty("App::PropertyInteger","uEnd").uEnd=-1
		
		obj.addProperty("App::PropertyInteger","vBegin")
		obj.addProperty("App::PropertyInteger","vEnd").vEnd=-1
		obj.addProperty("App::PropertyInteger","level")
		obj.addProperty("App::PropertyBool","uvSwap")
		obj.addProperty("App::PropertyBool","uReverse")
		obj.addProperty("App::PropertyBool","vReverse")
		obj.addProperty("App::PropertyBool","complement")
#		obj.addProperty("App::PropertyFloat","tangentFactorTube")
#		obj.addProperty("App::PropertyFloat","tangentFactorHelmet")




	def execute(self,fp):

		bs=fp.source.Shape.Face1.Surface
		luks=len(bs.getUKnots())
		lvks=len(bs.getVKnots())

		uks=bs.getUKnots()
		vks=bs.getVKnots()

#		fp.uBegin=1
#		fp.uEnd=-2
#		fp.vBegin=1
#		fp.vEnd=-2

		
		if not fp.complement:

			bs2=bs.copy()

	#		bs2.buildFromPolesMultsKnots(bs.getPoles(),
	#			um,vm,range(len(um)),range(len(vm)),
	#			False,False,3,3)
			bs2.segment(uks[fp.uBegin],uks[fp.uEnd],vks[fp.vBegin],vks[fp.vEnd])

			fp.Shape=bs2.toShape()

		else:
			comps=[]
			segs=[(0,fp.uBegin,0,-1),(fp.uEnd,-1,0,-1),
				(fp.uBegin,fp.uEnd,0,fp.vBegin),(fp.uBegin,fp.uEnd,fp.vEnd,-1)]
			for (a,b,c,d) in segs:
				
				try:
					bs2=bs.copy()
					bs2.segment(uks[a],uks[b],vks[c],vks[d])
					comps += [bs2.toShape()]
				except:
					print ("cannot create segment ",a,b,c,d)
					pass

			fp.Shape=Part.Compound(comps)
			fp.ViewObject.DisplayMode="Shaded"
			fp.ViewObject.Transparency=40






#-----------------



def selectionToNurbs():
	'''convert selection to a nurbs face and all edges tos nurbs curvse'''
	obj=Gui.Selection.getSelection()[0]
	f=obj.Shape.Face1
	print f
	n=f.toNurbs()
	sf=n.Face1.Surface
	for e in n.Edges:
		print e
		c=e.Curve
		Part.show(c.toShape())

	Part.show(sf.toShape())



def createYankee():
	'''create a yankee face (two finger)'''

	obj1=App.ActiveDocument.FaceConnection_Cell
	obj2=App.ActiveDocument.FaceConnection001_Cell001

	sf1=obj1.Shape.Face1.Surface
	sf2=obj2.Shape.Face1.Surface

	poles1=np.array(sf1.getPoles()).swapaxes(0,1)
	poles2=np.array(sf2.getPoles()).swapaxes(0,1)

	allp=np.concatenate([poles1,[2*poles1[-1]-poles1[-2],2*poles2[0]-poles2[1]],poles2])

	vmults=sf1.getUMultiplicities()
	vknots=range(len(vmults))

	print allp.shape
	lu=allp.shape[0]
	for i in range(2,7):
			allp[4,i]=allp[3,i]
			allp[5,i]=allp[3,i]

	print "lu.",lu
	umults=[4,3,3,4]
	uknots=range(len(umults))

	sf=Part.BSplineSurface()
	sf.buildFromPolesMultsKnots(
				allp,
				umults,
				vmults,
				uknots,
				vknots,
				False,False,3,3
			)
	sf.segment(1,2,0,1)
	Part.show(sf.toShape())


class QuadPm(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)
		obj.addProperty("App::PropertyPlacement","pointA")
		obj.addProperty("App::PropertyPlacement","pointB")
		obj.addProperty("App::PropertyPlacement","pointC")
		obj.addProperty("App::PropertyPlacement","pointD")

		obj.addProperty("App::PropertyLink","sourceA")
		obj.addProperty("App::PropertyLink","sourceB")
		obj.addProperty("App::PropertyLink","sourceC")
		obj.addProperty("App::PropertyLink","sourceD")

		
		obj.addProperty("App::PropertyLink","source")
		obj.addProperty("App::PropertyLink","curveB")
		obj.addProperty("App::PropertyLink","curveC")

#		obj.addProperty("App::PropertyString","edgeA")
#		obj.addProperty("App::PropertyString","edgeB")
#		obj.addProperty("App::PropertyString","edgeC")

		obj.addProperty("App::PropertyInteger","uBegin").uBegin=0
		obj.addProperty("App::PropertyInteger","uEnd").uEnd=-1
		
		obj.addProperty("App::PropertyInteger","vBegin")
		obj.addProperty("App::PropertyInteger","vEnd").vEnd=-1
		obj.addProperty("App::PropertyInteger","level")
		obj.addProperty("App::PropertyBool","uvSwap")
		obj.addProperty("App::PropertyBool","uReverse")
		obj.addProperty("App::PropertyBool","vReverse")
		obj.addProperty("App::PropertyBool","complement")
#		obj.addProperty("App::PropertyFloat","tangentFactorTube")
#		obj.addProperty("App::PropertyFloat","tangentFactorHelmet")



	def execute(self,fp):

		comps=[]
		if fp.sourceA <> None:
			fp.pointA=fp.sourceA.Placement
		if fp.sourceB <> None:
			fp.pointB=fp.sourceB.Placement
		if fp.sourceC <> None:
			fp.pointC=fp.sourceC.Placement
		if fp.sourceD <> None:
			fp.pointD=fp.sourceD.Placement



		try:
			comps += [Part.makePolygon([fp.pointA.Base,fp.pointB.Base])]
			comps += [Part.makePolygon([fp.pointB.Base,fp.pointD.Base])]
			comps += [Part.makePolygon([fp.pointC.Base,fp.pointD.Base])]
			comps += [Part.makePolygon([fp.pointC.Base,fp.pointA.Base])]
		except:
			pass
		fp.Shape=Part.Compound(comps)
		fp.ViewObject.Transparency=40



def createCell():

	sf=App.ActiveDocument.addObject('Part::FeaturePython','Cell')
	sf.ViewObject.ShapeColor=(random.random(),0.5+random.random(),random.random(),)
	Cell(sf)
	sf.source=Gui.Selection.getSelection()[0]
	ViewProvider(sf.ViewObject)




def createQuadPlacement():

	sf=App.ActiveDocument.addObject('Part::FeaturePython','QuadPM')
	sf.ViewObject.ShapeColor=(random.random(),0.5+random.random(),random.random(),)
	QuadPm(sf)
	ViewProvider(sf.ViewObject)
	
	sf.pointA=Gui.Selection.getSelection()[0].Placement
	sf.pointB=Gui.Selection.getSelection()[1].Placement
	sf.pointC=Gui.Selection.getSelection()[2].Placement
	sf.pointD=Gui.Selection.getSelection()[3].Placement

	sf.sourceA=Gui.Selection.getSelection()[0]
	sf.sourceB=Gui.Selection.getSelection()[1]
	sf.sourceC=Gui.Selection.getSelection()[2]
	sf.sourceD=Gui.Selection.getSelection()[3]


def checkCurveGUI():
	''' testcase checkcurve'''
	obj=Gui.Selection.getSelection()[0]
	curve=obj.Shape.Edge1.Curve
	checkcurve(curve)
	pass


def FaceToBezierSurface():
	'''selektierte flaeche in bspline surface umwandeln'''
	obj=Gui.Selection.getSelection()[0]
	a=Gui.Selection.getSelectionEx()[0]
	for s in a.SubObjects:
		print s
		n=s.toNurbs()
		sf=n.Face1.Surface
		sf.increaseDegree(3,3)
		print sf.getUKnots()
		print sf.getVKnots()
		print sf.getUMultiplicities()
		print sf.getVMultiplicities()

		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(sf.getPoles(),
			sf.getUMultiplicities(),sf.getVMultiplicities(),
			range(sf.NbUKnots),range(sf.NbVKnots),
			False,False,sf.UDegree,sf.VDegree,sf.getWeights())

		bs.insertUKnot(0.5,3,0)
		bs.insertVKnot(0.5,3,0)

		tt=App.ActiveDocument.addObject('Part::Spline',obj.Label +"_toNurbs")
		tt.Shape=bs.toShape()
		# tt.ViewObject.ControlPoints = True




def stretchandbend():
	#  transformation berechnen


	pass2=False
	pass2=0

	b=App.ActiveDocument.BePlane
	
	if pass2:
		b=App.ActiveDocument.Shape012
	
	sf=b.Shape.Face1.Surface
	poles=np.array(sf.getPoles())

	a=App.ActiveDocument.QuadPM
	vaa2=np.array([a.pointA.Base,a.pointB.Base,a.pointC.Base,a.pointD.Base])

	vaa2[0] -= poles[0,0]
	vaa2[1] -= poles[-1,0]
	vaa2[2] -= poles[0,-1]
	vaa2[3] -= poles[-1,-1]


	uc,vc,c=poles.shape
	poles2=poles.copy()
	for ui in range(uc):
		for vi in range(vc):
			poles2[ui,vi] +=  vaa2[3]*ui*vi/(uc-1)/(vc-1)
			poles2[ui,vi] +=  vaa2[2]*(uc-1-ui)*(vi)/(uc-1)/(vc-1)
			poles2[ui,vi] +=  vaa2[0]*(uc-1-ui)*(vc-1-vi)/(uc-1)/(vc-1)
			poles2[ui,vi] +=  vaa2[1]*(ui)*(vc-1-vi)/(uc-1)/(vc-1)




#	poles=poles2.reshape(a,b,3)

	bs=Part.BSplineSurface()
	bs.buildFromPolesMultsKnots(poles2,
			sf.getUMultiplicities(),sf.getVMultiplicities(),
			sf.getUKnots(),sf.getVKnots(),
			False,False,sf.UDegree,sf.VDegree)

	Part.show(bs.toShape())


	App.ActiveDocument.ActiveObject.Label="stretch "

	if pass2:
		return

	xd=FreeCAD.Vector(1,0,0)*4000
	yd=FreeCAD.Vector(0,1,0)*4000

	puA=a.pointA.Rotation.multVec(xd)
	pvA=a.pointA.Rotation.multVec(yd)

	puB=a.pointB.Rotation.multVec(xd)
	pvB=a.pointB.Rotation.multVec(yd)

	puC=a.pointC.Rotation.multVec(xd)
	pvC=a.pointC.Rotation.multVec(yd)

	puD=a.pointD.Rotation.multVec(xd)
	pvD=a.pointD.Rotation.multVec(yd)


	poles3=np.array([
	a.pointA.Base,a.pointA.Base+puA,a.pointB.Base-puB,a.pointB.Base,
	a.pointA.Base+pvA,a.pointA.Base+puA+pvA,a.pointB.Base-puB+pvB,a.pointB.Base+pvB,

	a.pointC.Base-pvC,a.pointC.Base+puC-pvC,a.pointD.Base-puD-pvD,a.pointD.Base-pvD,
	a.pointC.Base,a.pointC.Base+puC,a.pointD.Base-puD,a.pointD.Base]
	).reshape(4,4,3).swapaxes(0,1)
	
	bs3=Part.BSplineSurface()
	bs3.buildFromPolesMultsKnots(poles3,[4,4],[4,4],[0,1],[0,1],
			False,False,3,3,)


	# da s muss parametric werden
	bs3.insertUKnot(0.25,3,0)
	bs3.insertUKnot(0.5,3,0)
	bs3.insertUKnot(0.75,3,0)
	
	bs3.insertVKnot(0.33,3,0)
	bs3.insertVKnot(0.67,3,0)

	poles3=np.array(bs3.getPoles())

	bs=Part.BSplineSurface()
	bs.buildFromPolesMultsKnots(poles3,
			sf.getUMultiplicities(),sf.getVMultiplicities(),
			sf.getUKnots(),sf.getVKnots(),
			False,False,sf.UDegree,sf.VDegree)

	Part.show(bs.toShape())
	App.ActiveDocument.ActiveObject.Label="base"



#	bs=Part.BSplineSurface()
#	bs.buildFromPolesMultsKnots((poles2+poles3)*0.5,
#			sf.getUMultiplicities(),sf.getVMultiplicities(),
#			sf.getUKnots(),sf.getVKnots(),
#			False,False,sf.UDegree,sf.VDegree)
#	Part.show(bs.toShape())
#	App.ActiveDocument.ActiveObject.Label="stretch and morph"


#	bs=Part.BSplineSurface()
#	bs.buildFromPolesMultsKnots((poles2+poles3),
#			sf.getUMultiplicities(),sf.getVMultiplicities(),
#			sf.getUKnots(),sf.getVKnots(),
#			False,False,sf.UDegree,sf.VDegree)
#	Part.show(bs.toShape())
#	App.ActiveDocument.ActiveObject.Label="moprh only"


	poles=poles2+poles3

	a=App.ActiveDocument.QuadPM
	vaa2=np.array([a.pointA.Base,a.pointB.Base,a.pointC.Base,a.pointD.Base])

	vaa2[0] -= poles[0,0]
	vaa2[1] -= poles[-1,0]
	vaa2[2] -= poles[0,-1]
	vaa2[3] -= poles[-1,-1]


	uc,vc,c=poles.shape
	poles2=poles.copy()
	for ui in range(uc):
		for vi in range(vc):
			poles2[ui,vi] +=  vaa2[3]*ui*vi/(uc-1)/(vc-1)
			poles2[ui,vi] +=  vaa2[2]*(uc-1-ui)*(vi)/(uc-1)/(vc-1)
			poles2[ui,vi] +=  vaa2[0]*(uc-1-ui)*(vc-1-vi)/(uc-1)/(vc-1)
			poles2[ui,vi] +=  vaa2[1]*(ui)*(vc-1-vi)/(uc-1)/(vc-1)






#	poles=poles2.reshape(a,b,3)

	bs=Part.BSplineSurface()
	bs.buildFromPolesMultsKnots(poles2,
			sf.getUMultiplicities(),sf.getVMultiplicities(),
			sf.getUKnots(),sf.getVKnots(),
			False,False,sf.UDegree,sf.VDegree)

	Part.show(bs.toShape())
	App.ActiveDocument.ActiveObject.Label="stretch and morph v2 "




def AA():
	'''berechne  Verformungskraft'''
	ss=App.ActiveDocument.Sketch.Shape
	pts=[v.Point for v in ss.Vertexes]
	ptss=pts[1:]+pts[:1]

	#biegekraft
	lp=len(pts)
	su=0
	for i in range(1,lp-1):
		su += ((pts[i]-pts[i-1]).normalize().cross((pts[i+1]-pts[i]).normalize())).Length

	print ("Bend force",su)

	ss2=App.ActiveDocument.BeringSketch.Shape
	print ("Stretch force:",ss2.Curve.length())
	pls=ss2.Curve.getPoles()
	basel=0
	ll=(len(pls)-1)/3
	for i in range(ll):
		basel += (pls[3*i]-pls[3*i+3]).Length

	print basel





def AA():
	borderToWire()


def genbase(fp,pts,center=FreeCAD.Vector(),offset=2):
	# Basiszelle

	ptsa=[FreeCAD.Vector(p[0],p[1],p[2]) +center for p in pts]
	ptsb=ptsa[offset:]+ptsa[:offset]
	ptsb=ptsa
	
	sf=App.ActiveDocument.getObject(fp.Name+"_base")
	if sf == None:
		sk=App.ActiveDocument.addObject('Part::Spline',fp.Name+"_base")
		sk.ViewObject.hide()

	sk.Shape=Part.makePolygon(ptsb)
	aa=genk(0,0,1,FreeCAD.Vector(),sk,show=False)
	aa.ViewObject.hide()
	return aa,ptsa



def gencircle(fp,n,h=300,radius=400,center=None):

	c = 0.551915024494
	vv=radius*c

	ptsa = [
		[radius+vv,radius-vv],
		[radius,radius],
		[radius-vv,radius+vv],
		[-radius+vv,radius+vv],
		[-radius,radius],
		[-radius-vv,radius-vv],
		[-radius-vv,-radius+vv],
		[-radius,-radius],
		[-radius+vv,-radius-vv],
		[radius-vv,-radius-vv],
		[radius,-radius],
		[radius+vv,-radius+vv]
	]

#	pts2=ptsa[3:]+ptsa[:3]
	pts2=ptsa[6:]+ptsa[:6]


	ptsa=[FreeCAD.Vector(p[0],p[1],h)+center for p in pts2]
	rot=fp.location.Rotation

	ptsa=[rot.multVec(FreeCAD.Vector(p[0],p[1],h))+center for p in pts2]

	ptsb=ptsa[1:]+ptsa[:1]
	ptsb=ptsa
	sf=App.ActiveDocument.getObject(fp.Name+"_circle_"+str(n))
	if sf == None:
		sk=App.ActiveDocument.addObject('Part::Spline',fp.Name+"_circle_"+str(n))
		sk.ViewObject.hide()

	sk.ViewObject.hide()
	sk.Shape=Part.makePolygon(ptsb)


	source=App.ActiveDocument.ActiveObject
	bb=genk(0,0,1,FreeCAD.Vector(),source)
	bb.ViewObject.hide()
	return bb,ptsb



def createEndface(pts,label):
	# abschlussfleche erzeugen oben
	aa=np.array([pts[1:5],pts[4:8],pts[7:11][::-1],pts[7:11][::-1],]).reshape(4,4,3)

	aa[1,0]=pts[0]
	aa[1,3]=pts[5]
	aa[2,0]=pts[11]
	aa[2,3]=pts[6]

	bs3=Part.BSplineSurface()
	bs3.buildFromPolesMultsKnots(aa, [4,4],[4,4],[0,1],[0,1],False,False,3,3)

	sk=App.ActiveDocument.addObject('Part::Spline',label)
	#sk.ViewObject.hide()
	sk.Shape=bs3.toShape()



# MAIN -----------------





class HoleFace(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)

#		obj.addProperty("App::PropertyLinkList","ribs")
#		obj.addProperty("App::PropertyLinkList","meridians")
		obj.addProperty("App::PropertyLink","source")
#		obj.addProperty("App::PropertyInteger","uCount").uCount=3
#		obj.addProperty("App::PropertyInteger","vCount").vCount=3
#		obj.addProperty("App::PropertyInteger","uWeight").uWeight=10
#		obj.addProperty("App::PropertyInteger","vWeight").vWeight=10
		obj.addProperty("App::PropertyPlacement","location")



	def execute(self,fp):

		print "EXECute createHole"
		createHole(fp)



def createHole(fp,height=100):
	''' anschluss kreis an zelle '''

	obj=fp.source
	
	print "Location"
	print fp.location
	endfaces=False
	radius=4
	height=3
	
	# zelle
	pts=[
			[400,301],
			[400,400],
			[300,400],
			[-300,400],
			[-400,400],
			[-400,300],
			[-400,-300],
			[-400,-400],
			[-300,-400],
			[300,-400],
			[400,-400],
			[400,300]
	]


	print "get bool mikidebug:",getcb("mikidebug")
	#return

	poles=np.array(obj.Shape.Face1.Surface.getPoles())

	center=FreeCAD.Vector((poles[0,0]+poles[-1,-1])*0.5)+FreeCAD.Vector(2,-10,5)
	center += fp.location.Base



#	Draft.makePoint(center)

	print "-----------------"

	pts=[poles[-1,-2],
		poles[-1,-1],poles[-2,-1],poles[1,-1],poles[0,-1],
		poles[0,2],poles[0,1],poles[0,0],
		poles[1,0],poles[2,0],poles[3,0],poles[3,1]]

#	Draft.makeWire([FreeCAD.Vector(p) for p in pts])


	ta=time.time()
	n=0
	ptsu=pts[::-1]
	aa,ptsa=genbase(fp,ptsu,offset=6)
	hh=10
	bb,ptsb=gencircle(fp,1,hh+height*.5,radius=radius,center=center)
	cc,ptsc=gencircle(fp,2,hh+height,radius=radius,center=center)
	dd,ptsd=gencircle(fp,3,hh+height*2,radius=radius,center=center)

	sf=App.ActiveDocument.getObject(fp.Name+"_hole")
	if sf == None:
		sf=App.ActiveDocument.addObject('Sketcher::SketchObjectPython',fp.Name+"_hole")
		#sf.ViewObject.hide()
		_=Beface(sf)
	
	sf.berings=[aa,bb,cc,dd]
	#sf.berings=[bb,cc,dd]
	ViewProvider(sf.ViewObject)

#	bg=App.ActiveDocument.addObject('Part::FeaturePython','BeGrid')
#	bg.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
#	BeGrid(bg)
#
#	ViewProvider(bg.ViewObject)
#	bg.Source=sf

	# bg.ViewObject.show()

	print
	print time.time()-ta
#	App.activeDocument().recompute()
#	Gui.updateGui()

	if endfaces:
		createEndface(ptsd,"oben")
		createEndface(ptsc,"mitte")
		createEndface(ptsa,"unten")




def createHoleGUI():
	'''Gui for creater of a hole'''


	class MyApp(MikiApp):

		def run(self):
			createHole(height=self.root.ids['height'].value())
			App.activeDocument().recompute()

	layout = '''
MainWindow:
	QtGui.QLabel:
		setText:"***  Gordon Hole configuration  ***"
	VerticalLayout:
		HorizontalGroup:
			setTitle: "Layout"
			QtGui.QSlider:
				id: 'height'
				setMinimum: -100.
				setValue: 30.0
				setMaximum: 100.0
				setOrientation: PySide.QtCore.Qt.Orientation.Horizontal
	#			valueChanged.connect: app.run
		QtGui.QPushButton:
			setText: "run"
			clicked.connect: app.run
		QtGui.QPushButton:
			setText: "close"
			clicked.connect: app.close
	setSpacer:
	'''


	mikigui = createMikiGui2(layout, MyApp)
	return mikigui



	'''Gui for creater of a hole'''


def createHoleGUI():
#	createHole(
#		height=10,
#	)

	bg=App.ActiveDocument.addObject('Part::FeaturePython','HoleFace')
	bg.ViewObject.ShapeColor=(0.5+random.random(),random.random(),random.random(),)
	HoleFace(bg)
	bg.source=Gui.Selection.getSelection()[0]
	

	ViewProvider(bg.ViewObject)
	App.activeDocument().recompute()






class GordonFace(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)

		obj.addProperty("App::PropertyLinkList","ribs")
		obj.addProperty("App::PropertyLinkList","meridians")
		obj.addProperty("App::PropertyLink","grid")
		obj.addProperty("App::PropertyInteger","uCount").uCount=3
		obj.addProperty("App::PropertyInteger","vCount").vCount=3
		obj.addProperty("App::PropertyInteger","uWeight").uWeight=10
		obj.addProperty("App::PropertyInteger","vWeight").vWeight=10



	def execute(self,fp):

		print "EXECute GORDON"
		createGordon(fp,scale=5.0)







def createGordon(obj,scale=5.0):




	if obj.ribs<>None:
		polsu=np.array([a.Shape.Edge1.Curve.getPoles() for a in obj.ribs])
		suc=len(obj.ribs)-1
	if obj.meridians<>None:
		polsv=np.array([a.Shape.Edge1.Curve.getPoles() for a in obj.meridians])
		svc=len(obj.meridians)-1

	if obj.grid<>None:
		
		suc=obj.uCount-1
		svc=obj.vCount-1
		try: 
			print obj.grid.Links
			polsu=np.array([a.Shape.Edge1.Curve.getPoles() for a in obj.grid.Links[0:suc+1]])
			polsv=np.array([a.Shape.Edge1.Curve.getPoles() for a in obj.grid.Links[suc+1:suc+svc+2]])

		except:
			a=obj.grid
			lenedges=[len(e.Curve.getPoles()) for e in a.Shape.Edges]
			print lenedges
			vcc=(lenedges[0]+2)/3
			ucc=(lenedges[-1]+2)/3
			print (ucc,vcc,len(lenedges))
			assert ucc+vcc==len(lenedges)
			obj.uCount=ucc
			obj.vCount=vcc
			suc=obj.uCount-1
			svc=obj.vCount-1

			polsu=np.array([a.Shape.Edges[i].Curve.getPoles() for i in range(0,suc+1)])
			polsv=np.array([a.Shape.Edges[i].Curve.getPoles() for i in range(suc+1,suc+svc+2)])

			assert polsu.shape==(ucc,lenedges[0],3)
			assert polsv.shape==(vcc,lenedges[-1],3)


	print "shapes u v "
	print polsu.shape
	print polsv.shape

#	suc=3
#	svc=2


	#return

#	return
	if 0: # mein beispiel
		es=App.ActiveDocument.BeGrid.Shape.Edges

		poles=[]
		for e in es:
			poles += [e.Curve.getPoles()]


		#anzahl segmente
		suc=3 # 
		svc=3

		polsu=np.array(poles[0:suc+1])
		polsv=np.array(poles[suc+1:suc+svc+2])


	def blender(c,t):
		if abs(c-t)>=1.: rc=0
		else:
			rc=(1-min(abs(c-t),1))**0.7
#		print ("blender c,t",c,t,rc)
		return rc


	def Xblender(c,t):
		if abs(c-t)>=1.: rc=0
		else:
			rc=  (c+1-t)*(c-1-t)*(-1)
		print ("blender c,t",c,t,rc)
		return rc


	s3tt=np.zeros((3*suc+1)*(3*svc+1)*3).reshape(3*suc+1,3*svc+1,3)

	dd=scale*0.01
	uli=[0,dd]
	for i in range(1,suc):
		uli += [i-dd,i,i+dd]
	uli += [suc-dd,suc]
	vli=[0,dd]
	for i in range(1,svc):
		vli += [i-dd,i,i+dd]
	vli += [svc-dd,svc]


	if 10:
		for ui,u in enumerate(uli):
			for vi,v in enumerate(vli):
				print ("ui,vi",ui,vi)
				for i in range(suc+1):
					for j in range(svc+1):
						print ("i,j,blender",i,j,blender(j,v),blender(i,u))
	#					s3tt[ui,vi] += (polsu[i][3*j]*obj.uWeight+polsv[j][3*i]*obj.vWeight)*blender(i,u)/blender(i,i)*blender(j,v)/blender(j,j)/(obj.uWeight+obj.vWeight)
	#					print s3tt[ui,vi]
	#					print polsu[i][3*j]
						s3tt[ui,vi] += (polsu[i][3*j])*blender(i,u)/blender(i,i)*blender(j,v)/blender(j,j)




		mu=[4]+[3]*(suc-1)+[4]
		mv=[4]+[3]*(svc-1)+[4]
		ag=Part.BSplineSurface()
		ag.buildFromPolesMultsKnots(s3tt, 
				mu,mv,range(suc+1),range(svc+1),
				False,False,3,3)

		name="gordonS3"
		tt=App.ActiveDocument.getObject(name)
		if tt==None:
			tt=App.ActiveDocument.addObject('Part::Spline',name)
		tt.Shape=ag.toShape()

	ptsarr=[]
	for ui,u in enumerate(uli):
		pts=np.zeros((3*svc+1)*3).reshape(1,3*svc+1,3)
		for i in range(suc+1):
			pts += [polsu[i]*blender(i,u)/blender(i,i)]
		ptsa=[FreeCAD.Vector(p) for p in pts[0]]
		ptsarr += [ptsa]

	ag=Part.BSplineSurface()
	ag.buildFromPolesMultsKnots(np.array(ptsarr), 
			mu,mv,range(suc+1),range(svc+1),
			False,False,3,3)

	name="gordonU"
	tt=App.ActiveDocument.getObject(name)
	if tt==None:
		tt=App.ActiveDocument.addObject('Part::Spline',name)
	tt.Shape=ag.toShape()

	ptsarr2=[]
	
	for vi,v in enumerate(vli):
		pts=np.zeros((3*suc+1)*3).reshape(1,3*suc+1,3)
		print ("shapes",suc,svc)
		print pts.shape
		print polsv.shape
		for i in range(svc+1):
			pts += [polsv[i]*blender(i,v)/blender(i,i)]
		ptsa=[FreeCAD.Vector(p) for p in pts[0]]
		ptsarr2 += [ptsa]

	ag=Part.BSplineSurface()
	ag.buildFromPolesMultsKnots(np.array(ptsarr2), 
			mv,mu,range(svc+1),range(suc+1),
			False,False,3,3)

	name="gordonV"
	tt=App.ActiveDocument.getObject(name)
	if tt==None:
		tt=App.ActiveDocument.addObject('Part::Spline',name)
	tt.Shape=ag.toShape()


	if 0:
		ptsarr3=(np.array(ptsarr) +np.array(ptsarr2).swapaxes(0,1)-s3tt)

	#	ptsarr3=(np.array(ptsarr) +np.array(ptsarr2).swapaxes(0,1))*0.5



		ag=Part.BSplineSurface()
		ag.buildFromPolesMultsKnots(ptsarr3, 
				mu,mv,range(suc+1),range(svc+1),
				False,False,3,3)

		name="gordon"
		tt=App.ActiveDocument.getObject(name)
		if tt==None:
			tt=App.ActiveDocument.addObject('Part::Spline',name)
		tt.Shape=ag.toShape()

	ptsarr3=(np.array(ptsarr)*2*obj.uWeight/(obj.uWeight+obj.vWeight) +np.array(ptsarr2).swapaxes(0,1)*2*obj.vWeight/(obj.uWeight+obj.vWeight)-s3tt)

	# RANDER ..
	print  "raaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	ptsarr3[0]=polsu[-1]
	ptsarr3[-1]=polsu[0]



	ag=Part.BSplineSurface()
	ag.buildFromPolesMultsKnots(ptsarr3, 
			mu,mv,range(suc+1),range(svc+1),
			False,False,3,3)

	obj.Shape=ag.toShape()


def aGUI():
	'''Gui dialog for  template/later'''

	class App(MikiApp):

		def run(self):
			name="Gordon"
			tt=App.ActiveDocument.getObject(name)
			if 1 or tt==None:
				tt=App.ActiveDocument.addObject('Part::FeaturePython',"???")
				GordonFace(tt)

				if 0:
					tt.meridians=[
							App.ActiveDocument.BeringSketch,
							App.ActiveDocument.BeringSketch001,
							App.ActiveDocument.BeringSketch002,
						]


					tt.ribs=[
						App.ActiveDocument.BeringSketch003,
						App.ActiveDocument.BeringSketch005,
						App.ActiveDocument.BeringSketch004,
					]
				else:
					rr.grid=App.ActiveDocument.Compound
				
			createGordon(tt,self.root.ids['scale'].value())
			#tt.Shape=shape
			ViewProvider(tt.ViewObject)
			App.activeDocument().recompute()


	layout = '''
MainWindow:
	QtGui.QLabel:
		setText:"***  Gordon Surface configuration  ***"
	VerticalLayout:
		HorizontalGroup:
			setTitle: "tangent Force"
			QtGui.QSlider:
				id: 'scale'
				setMinimum: 1
				setValue: 30.0
				setMaximum: 100.0
				setOrientation: PySide.QtCore.Qt.Orientation.Horizontal
	#			valueChanged.connect: app.run
		QtGui.QPushButton:
			setText: "run"
			clicked.connect: app.run
		QtGui.QPushButton:
			setText: "close"
			clicked.connect: app.close
	setSpacer:
	'''


	mikigui = createMikiGui2(layout, YYApp)
	return mikigui




def createGordonGUI():
	'''variant ohne dialog'''
	name="Gordon"
	tt=App.ActiveDocument.getObject(name)
	if 1 or tt==None:
		tt=App.ActiveDocument.addObject('Part::FeaturePython',"Gordon")
		GordonFace(tt)

		if 0:
			tt.meridians=[
					App.ActiveDocument.BeringSketch,
					App.ActiveDocument.BeringSketch001,
					App.ActiveDocument.BeringSketch002,
				]


			tt.ribs=[
				App.ActiveDocument.BeringSketch003,
				App.ActiveDocument.BeringSketch005,
				App.ActiveDocument.BeringSketch004,
			]
		else:
			# compound in richtiger reihenfolge
			#tt.grid=App.ActiveDocument.Compound
			# grid anorndung von begrid
#			tt.grid=App.ActiveDocument.BeGrid
			tt.grid=Gui.Selection.getSelection()[0]
			try:
				tt.uCount=tt.grid.Source.uSegments+1
				tt.vCount=tt.grid.Source.vSegments+1
			except:
				pass
			

	ViewProvider(tt.ViewObject)
	createGordon(tt)
	#tt.Shape=shape
	
	App.activeDocument().recompute()





def compareMaps():
	'''vergleich zwei Maps '''
	(ma,mb)=Gui.Selection.getSelection()
	comp=[]
	for p,q in zip(ma.Shape.Vertexes,mb.Shape.Vertexes):
		if (p.Point-q.Point).Length >0:
			comp += [Part.makePolygon([p.Point,q.Point])]

	Part.show(Part.Compound(comp))



def BB():
	compareMaps()





def  polishG1GUI():
	''' make surface G1 continues'''

	obj=Gui.Selection.getSelection()[0]
	sf=obj.Shape.Face1.Surface
	poles=np.array(sf.getPoles())


	def mod(u,v):
		seg=poles[3*u-1:3*u+3,3*v-1:3*v+3]
		# print seg.shape

		b=seg[1,1]

		te=seg[2,1]-b
		tw=seg[0,1]-b
		tn=seg[1,2]-b
		ts=seg[1,0]-b

	#	print te,tw

		te=FreeCAD.Vector(te)
		tw=FreeCAD.Vector(tw)
		fe=te.Length/(te.Length+tw.Length)
		fw=tw.Length/(te.Length+tw.Length)


		tn=FreeCAD.Vector(tn)
		ts=FreeCAD.Vector(ts)
		fn=tn.Length/(tn.Length+ts.Length)
		fs=ts.Length/(tn.Length+ts.Length)

		# parallel ?
		if te.cross(tw).Length >10**-5:
			print ("run",u,v)
			print "ost west nicht parallel"
			print te.cross(tw).Length


			tu=(te+tw)

	#		print tu
	#		print fe
	#		print fw

			seg[2,1] -= fe*tu
			seg[0,1] -= fw*tu


		# parallel ?
		if tn.cross(ts).Length >10**-5:
			print ("run",u,v)
			print "nord sued nicht parallel"
			print tn.cross(ts).Length
			tu=(tn+ts)

	#		print tu
	#		print fn
	#		print fs

			seg[1,2] -= fn*tu
			seg[1,0] -= fs*tu

		seg[0,0]=seg[0,1]+seg[1,0]-seg[1,1]
		seg[0,2]=seg[0,1]+seg[1,2]-seg[1,1]
		seg[2,0]=seg[1,0]+seg[2,1]-seg[1,1]
		seg[2,2]=seg[1,2]+seg[2,1]-seg[1,1]

		poles[3*u-1:3*u+3,3*v-1:3*v+3]=seg

	for u in [1,2,3,4,5,6]:
		for v in [1,2,3,4,5,6]:
			try:
				mod(u,v)
				mod(u,v)
			except: pass

	bs=Part.BSplineSurface()
	bs.buildFromPolesMultsKnots(poles, 
				sf.getUMultiplicities(),sf.getVMultiplicities(),
				sf.getUKnots(),sf.getVKnots(),
				False,False,3,3)
	Part.show(bs.toShape())



	if 0: #erzeuge unstete flaeche

		sf=App.ActiveDocument.ProductFace001.Shape.Face1.Surface
		poles2=np.array(sf.getPoles())
		a,b,c=poles2.shape
		poles2=poles2.reshape(a*b*c) + (15-np.random.random(a*b*c)*30)
		poles2=poles2.reshape(a,b,c)

		bs=Part.BSplineSurface()
		bs.buildFromPolesMultsKnots(poles2, 
								sf.getUMultiplicities(),sf.getVMultiplicities(),
								sf.getUKnots(),sf.getVKnots(),
								False,False,3,3)

		Part.show(bs.toShape())


	#+#
	

def AA():
	#selectionToNurbs()
	obj=App.ActiveDocument.result001
	pp=(App.ActiveDocument.result001.Shape.PrincipalProperties)
	for p in pp:
		print (p,pp[p])
	pm=np.array(pp['Moments'])
	print pm/min(pm)

def createTangentHelpersGUI():
	for obj in Gui.Selection.getSelection():
		axis2= obj.Shape.PrincipalProperties['FirstAxisOfInertia']
		print axis2
		axis2 *=400

		cp=App.ActiveDocument.copyObject(obj)
		cp.Placement.Base = -axis2 

		cp=App.ActiveDocument.copyObject(obj)
		cp.Placement.Base += axis2



class Border(FeaturePython):

	def __init__(self, obj):
		FeaturePython.__init__(self, obj)

		obj.addProperty("App::PropertyLink","source")
		obj.addProperty("App::PropertyInteger","offset")
		obj.addProperty("App::PropertyBool","reverse")



	def execute(self,fp):

		print "EXECute border"


#	def borderToWire():
		'''create a closed path olf the border poles of a bspline surface'''

		# mache zelle zu ring
		obj=fp.source
		bs=obj.Shape.Face1.Surface

		luks=len(bs.getUKnots())
		lvks=len(bs.getVKnots())

		uks=bs.getUKnots()
		vks=bs.getVKnots()

		comps=[]
		stripes=[
			[0,1],
			[-2,-1]
		]

		poles=np.array(bs.getPoles())
		poles2=poles.swapaxes(0,1)

		pts=np.concatenate([
			poles[0],
			poles2[-1],
			poles[-1][::-1],
			poles2[0][::-1],

		])

		pts=np.concatenate([
			poles[0][:-1],
			poles2[-1][:-1],
			poles[-1][::-1][:-1],
			poles2[0][::-1][:-1],

		])


		pts=[FreeCAD.Vector(p) for p in pts]
		offset=2
		offset=7
		offset=4
		offset=fp.offset
		print len(pts)
		pts2=pts[offset:]+pts[:offset]
#		pts2=pts[offset:]
		if fp.reverse:
			pts2=pts2[::-1]
		print len(pts)
		fp.Shape=Part.makePolygon(pts2)




def createBorderGUI():
	tt=App.ActiveDocument.addObject('Part::FeaturePython',"Border")
	Border(tt)
	tt.source=Gui.Selection.getSelection()[0]
	ViewProvider(tt.ViewObject)
	App.activeDocument().recompute()
