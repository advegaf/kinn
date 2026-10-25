"""Blender node and mesh helpers for the showcase renders. Units: metres."""
import math

import bpy
from mathutils import Vector

mm = 0.001


def mat(name, color, rough=0.5, metallic=0.0, emission=None, strength=1.0, image=None, sss=0.0, sss_scale=0.002):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Scale"].default_value = sss_scale
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.35)
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image)
        tex.extension = "EXTEND"
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = strength
    return m


def bsdf(m):
    return m.node_tree.nodes["Principled BSDF"]


def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
        else:
            setattr(n, k, v)
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def M(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def maprange(nt, v, a, b, lo=0.0, hi=1.0):
    n = N(nt, "ShaderNodeMapRange")
    n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = a, b
    n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = lo, hi
    n.clamp = True
    L(nt, v, n.inputs["Value"])
    return n.outputs["Result"]


def bump(nt, height, distance, strength=1.0):
    n = N(nt, "ShaderNodeBump", Strength=strength, Distance=distance)
    L(nt, height, n.inputs["Height"])
    L(nt, n.outputs["Normal"], bsdf_of(nt).inputs["Normal"])
    return n


def bsdf_of(nt):
    return nt.nodes["Principled BSDF"]


def obj_coords(nt):
    return N(nt, "ShaderNodeTexCoord").outputs["Object"]


def select(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def smooth(o, angle=35):
    select(o)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))


def new_obj(name, me):
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location, e.rotation_euler = loc, rot
    return e


def parent(objs, p):
    for o in objs:
        o.parent = p


def lathe(name, profile, material, steps=96, subsurf=2, loc=(0, 0, 0)):
    """Revolve an open (r, z) polyline around z. Profile runs from the axis round to the axis."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(r, 0, z) for r, z in profile], [(i, i + 1) for i in range(len(profile) - 1)], [])
    o = new_obj(name, me)
    o.location = loc
    s = o.modifiers.new("screw", "SCREW")
    s.axis, s.steps, s.render_steps = "Z", steps, steps
    s.use_merge_vertices, s.merge_threshold = True, 1e-6
    s.use_normal_calculate = True
    if subsurf:
        d = o.modifiers.new("subd", "SUBSURF")
        d.levels = d.render_levels = subsurf
    me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    smooth(o, 180)
    return o


def rr_points(w, h, r, seg=12):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(name, w, h, t, r, material, z0=0.0, uv=False, seg=12):
    """Rounded rectangle slab, centred in xy, from z0 to z0 + t. Optional planar UVs over w x h."""
    pts = rr_points(w, h, r, seg)
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z0 + t) for x, y in pts]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = new_obj(name, me)
    if uv:
        lay = me.uv_layers.new()
        for loop in me.loops:
            co = me.vertices[loop.vertex_index].co
            lay.data[loop.index].uv = (co.x / w + 0.5, co.y / h + 0.5)
    me.materials.append(material)
    return o


def bevel(o, width, segs=4):
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments, b.limit_method = width, segs, "ANGLE"
    b.harden_normals = False
    for p in o.data.polygons:
        p.use_smooth = True
    smooth(o, 40)
    return o


def cube(name, size, loc, material, bev=0.0, segs=3, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bev:
        bevel(o, bev, segs)
    return o


def curve(name, pts, radius, material, order=4):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = radius, 4, True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.use_endpoint_u, sp.order_u = True, min(order, len(pts))
    sp.resolution_u = 24
    cu.materials.append(material)
    return new_obj(name, cu)


def sphere(name, loc, scale, material, rot=(0, 0, 0), seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o


def look(o, target, up="Y"):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", up).to_euler()
