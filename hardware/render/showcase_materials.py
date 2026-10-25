"""Procedural materials for the showcase renders."""
import math

from showcase_build import L, M, N, bsdf, bsdf_of, bump, maprange, mat, obj_coords


def wood_mat():
    m = mat("oak", (0.4, 0.25, 0.14), rough=0.42)
    nt = m.node_tree
    b = bsdf_of(nt)
    b.inputs["Coat Weight"].default_value = 0.25
    b.inputs["Coat Roughness"].default_value = 0.18
    co = obj_coords(nt)
    sep = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, co, sep.inputs[0])
    plank = M(nt, "FLOOR", M(nt, "DIVIDE", sep.outputs["Y"], 0.16))
    seam = M(nt, "FRACT", M(nt, "DIVIDE", sep.outputs["Y"], 0.16))
    groove = M(nt, "MAXIMUM", maprange(nt, seam, 0.012, 0.0), maprange(nt, seam, 0.988, 1.0))
    # per-plank offset so the grain does not line up across seams
    wn = N(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="1D")
    L(nt, plank, wn.inputs["W"])
    comb = N(nt, "ShaderNodeCombineXYZ")
    L(nt, M(nt, "ADD", M(nt, "MULTIPLY", sep.outputs["X"], 0.22), M(nt, "MULTIPLY", wn.outputs["Value"], 7.0)), comb.inputs["X"])
    L(nt, M(nt, "MULTIPLY", sep.outputs["Y"], 1.0), comb.inputs["Y"])
    L(nt, sep.outputs["Z"], comb.inputs["Z"])
    wave = N(nt, "ShaderNodeTexWave", bands_direction="Y", Scale=55.0, Distortion=9.0, Detail=5.0)
    wave.inputs["Detail Scale"].default_value = 1.4
    L(nt, comb.outputs[0], wave.inputs["Vector"])
    fine = N(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=6.0)
    L(nt, comb.outputs[0], fine.inputs["Vector"])
    ramp = N(nt, "ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.2, 0.1, 0.045, 1)
    ramp.color_ramp.elements[1].color = (0.42, 0.25, 0.13, 1)
    grain = M(nt, "ADD", M(nt, "MULTIPLY", wave.outputs["Fac"], 0.75), M(nt, "MULTIPLY", fine.outputs["Fac"], 0.25))
    L(nt, M(nt, "ADD", grain, M(nt, "MULTIPLY", M(nt, "SUBTRACT", wn.outputs["Value"], 0.5), 0.25)), ramp.inputs["Fac"])
    dark = N(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    L(nt, groove, dark.inputs["Factor"])
    L(nt, ramp.outputs["Color"], dark.inputs[6])
    dark.inputs[7].default_value = (0.25, 0.18, 0.12, 1)
    L(nt, dark.outputs[2], b.inputs["Base Color"])
    L(nt, maprange(nt, wave.outputs["Fac"], 0, 1, 0.34, 0.52), b.inputs["Roughness"])
    bump(nt, M(nt, "SUBTRACT", M(nt, "MULTIPLY", wave.outputs["Fac"], 0.3), groove), 0.0012)
    return m


def linen_mat(name, color, scale=1.0):
    m = mat(name, color, rough=0.85)
    nt = m.node_tree
    b = bsdf_of(nt)
    b.inputs["Sheen Weight"].default_value = 0.25
    b.inputs["Sheen Roughness"].default_value = 0.4
    co = obj_coords(nt)
    w1 = N(nt, "ShaderNodeTexWave", bands_direction="X", Scale=700.0 * scale, Distortion=0.8, Detail=0.0)
    w2 = N(nt, "ShaderNodeTexWave", bands_direction="Y", Scale=700.0 * scale, Distortion=0.8, Detail=0.0)
    nz = N(nt, "ShaderNodeTexNoise", Scale=90.0 * scale, Detail=8.0)
    slub = N(nt, "ShaderNodeTexNoise", Scale=12.0 * scale, Detail=3.0)
    for t in (w1, w2, nz, slub):
        L(nt, co, t.inputs["Vector"])
    weave = M(nt, "MAXIMUM", w1.outputs["Fac"], w2.outputs["Fac"])
    h = M(nt, "ADD", M(nt, "MULTIPLY", weave, 0.6), M(nt, "MULTIPLY", nz.outputs["Fac"], 0.4))
    bump(nt, h, 0.0005, 1.0)
    tint = N(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    L(nt, maprange(nt, slub.outputs["Fac"], 0.3, 0.7, 0.0, 0.4), tint.inputs["Factor"])
    tint.inputs[6].default_value = (*color, 1)
    tint.inputs[7].default_value = (0.78, 0.72, 0.64, 1)
    L(nt, tint.outputs[2], b.inputs["Base Color"])
    return m


def ceramic_mat(name, color, speck=True, rough=0.1):
    m = mat(name, color, rough=rough, sss=0.12, sss_scale=0.003)
    nt = m.node_tree
    b = bsdf_of(nt)
    b.inputs["Coat Weight"].default_value = 0.4
    b.inputs["Coat Roughness"].default_value = 0.05
    if speck:
        co = obj_coords(nt)
        nz = N(nt, "ShaderNodeTexNoise", Scale=900.0, Detail=1.0)
        L(nt, co, nz.inputs["Vector"])
        mix = N(nt, "ShaderNodeMix", data_type="RGBA")
        L(nt, maprange(nt, nz.outputs["Fac"], 0.66, 0.70), mix.inputs["Factor"])
        mix.inputs[6].default_value = (*color, 1)
        mix.inputs[7].default_value = (0.25, 0.18, 0.13, 1)
        L(nt, mix.outputs[2], b.inputs["Base Color"])
        wob = N(nt, "ShaderNodeTexNoise", Scale=30.0, Detail=2.0)
        L(nt, co, wob.inputs["Vector"])
        bump(nt, wob.outputs["Fac"], 0.0002, 0.3)
    return m


def concha_mat(name, topping):
    """Bread dome with a sugar topping scored in a shell pattern. Object coords: dome base at z=0, r=45 mm."""
    m = mat(name, (0.6, 0.35, 0.15), rough=0.75, sss=0.05)
    nt = m.node_tree
    b = bsdf_of(nt)
    co = obj_coords(nt)
    sep = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, co, sep.inputs[0])
    x = M(nt, "DIVIDE", sep.outputs["X"], 0.045)
    y = M(nt, "DIVIDE", sep.outputs["Y"], 0.045)
    r = M(nt, "SQRT", M(nt, "ADD", M(nt, "MULTIPLY", x, x), M(nt, "MULTIPLY", y, y)))
    th = M(nt, "ARCTAN2", y, x)
    wob = N(nt, "ShaderNodeTexNoise", Scale=40.0, Detail=2.0)
    L(nt, co, wob.inputs["Vector"])
    jit = M(nt, "SUBTRACT", wob.outputs["Fac"], 0.5)
    r = M(nt, "ADD", r, M(nt, "MULTIPLY", jit, 0.12))
    th = M(nt, "ADD", th, M(nt, "MULTIPLY", jit, 0.5))
    # swirling ribs from the crown plus two growth rings: the concha shell
    u = M(nt, "ADD", M(nt, "MULTIPLY", th, 11 / (2 * math.pi)), M(nt, "MULTIPLY", r, 1.1))
    ribs = maprange(nt, M(nt, "ABSOLUTE", M(nt, "SUBTRACT", M(nt, "FRACT", u), 0.5)), 0.445, 0.5)
    rings = maprange(nt, M(nt, "ABSOLUTE", M(nt, "SUBTRACT", M(nt, "FRACT", M(nt, "MULTIPLY", r, 3.2)), 0.5)), 0.45, 0.5)
    groove = M(nt, "MULTIPLY", M(nt, "MAXIMUM", ribs, rings), maprange(nt, r, 0.12, 0.3))
    edge_n = N(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=3.0)
    L(nt, co, edge_n.inputs["Vector"])
    zt = M(nt, "ADD", sep.outputs["Z"], M(nt, "MULTIPLY", M(nt, "SUBTRACT", edge_n.outputs["Fac"], 0.5), 0.006))
    top = maprange(nt, zt, 0.0145, 0.0165)
    sugar = M(nt, "MULTIPLY", top, M(nt, "SUBTRACT", 1.0, groove))
    crumb = N(nt, "ShaderNodeTexNoise", Scale=400.0, Detail=4.0)
    L(nt, co, crumb.inputs["Vector"])
    bread = N(nt, "ShaderNodeMix", data_type="RGBA")
    L(nt, maprange(nt, sep.outputs["Z"], 0.0, 0.02), bread.inputs["Factor"])
    bread.inputs[6].default_value = (0.36, 0.17, 0.06, 1)
    bread.inputs[7].default_value = (0.5, 0.26, 0.08, 1)
    col = N(nt, "ShaderNodeMix", data_type="RGBA")
    L(nt, sugar, col.inputs["Factor"])
    L(nt, bread.outputs[2], col.inputs[6])
    shade = N(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    L(nt, maprange(nt, crumb.outputs["Fac"], 0.3, 0.7, 0.0, 0.12), shade.inputs["Factor"])
    shade.inputs[6].default_value = (*topping, 1)
    shade.inputs[7].default_value = (0.75, 0.7, 0.65, 1)
    L(nt, shade.outputs[2], col.inputs[7])
    L(nt, col.outputs[2], b.inputs["Base Color"])
    L(nt, maprange(nt, sugar, 0, 1, 0.8, 0.95), b.inputs["Roughness"])
    bump(nt, M(nt, "ADD", M(nt, "MULTIPLY", sugar, 1.0), M(nt, "MULTIPLY", crumb.outputs["Fac"], 0.35)), 0.0025)
    return m


def glass_mat():
    m = mat("glass", (0.97, 0.98, 0.97), rough=0.02)
    b = bsdf(m)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.47
    return m


def plaster_mat(color):
    m = mat("plaster", color, rough=0.92)
    nt = m.node_tree
    nz = N(nt, "ShaderNodeTexNoise", Scale=18.0, Detail=10.0, Roughness=0.62)
    L(nt, obj_coords(nt), nz.inputs["Vector"])
    bump(nt, nz.outputs["Fac"], 0.002, 0.25)
    return m
