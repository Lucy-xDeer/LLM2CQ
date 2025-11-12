wp = cq.Workplane('XY')
sk = cq.Sketch().rect(60, 40).vertices().fillet(5)
result = wp.placeSketch(sk).extrude(10)