import os
import re
import xml.etree.ElementTree as ET
import bpy

def get_texture_dictionary_name(xml_path):
    """
    Parses a YDR or YFT XML to find the referenced TextureDictionary name.
    """
    if not os.path.exists(xml_path):
        return None
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Look for TextureDictionary element
        tex_dict = root.find("TextureDictionary")
        if tex_dict is not None and tex_dict.text:
            return tex_dict.text.strip()
            
        # Sometimes it's inside a Drawable or Fragment
        for elem in root.iter("TextureDictionary"):
            if elem.text:
                return elem.text.strip()
    except Exception as e:
        print(f"[WUABO Nexus] Error parsing XML {xml_path}: {e}")
    
    return None

def find_sollumz_parent(obj):
    """
    Finds the Sollumz root parent of an object (Drawable, Fragment, etc.).
    """
    curr = obj
    while curr:
        if getattr(curr, "sollum_type", "") in {"sollumz_drawable", "sollumz_fragment", "sollumz_drawable_dictionary"}:
            return curr
        curr = curr.parent
    return None

def get_lod_score(obj):
    """
    Returns a score based on the LOD level of the object.
    Very High = 4, High = 3, Medium = 2, Low = 1, Very Low = 0.
    """
    sz_props = getattr(obj.data, "drawable_model_properties", None)
    if not sz_props: 
        sz_props = getattr(obj, "drawable_model_properties", None)
    
    lod = getattr(sz_props, "sollum_lod", "") if sz_props else ""
    
    if lod == "sollumz_veryhigh": return 4
    if lod == "sollumz_high": return 3
    if lod == "sollumz_medium": return 2
    if lod == "sollumz_low": return 1
    if lod == "sollumz_verylow": return 0
    
    nl = obj.name.lower()
    if "_vh" in nl or "_veryhigh" in nl: return 4
    if "_hi" in nl or "high" in nl or "_l0" in nl: return 3
    if "_med" in nl or "_l1" in nl: return 2
    if "_low" in nl or "_l2" in nl: return 1
    if "_vlow" in nl or "_l3" in nl or "_l4" in nl: return 0
    
    return 3 # Default to high-ish if unknown

def clean_number_suffix(name):
    """Removes Blender's .001 suffixes."""
    return re.sub(r'\.\d{3}$', '', name)

def get_base_name(name):
    """Removes LOD suffixes from names."""
    n = clean_number_suffix(name).lower()
    for s in ("_l0", "_l1", "_l2", "_l3", "_l4", "_vh", "_hi", "_high", "_med", "_low", "_vlow"):
        if n.endswith(s): 
            return n[:-len(s)]
    return n

def flatten_textures(temp_dir):
    """
    Moves all .dds files from subdirectories to the root temp_dir.
    CodeWalker API often exports textures into a subfolder named after the YDR.
    """
    import shutil
    count = 0
    for root, dirs, files in os.walk(temp_dir):
        if root == temp_dir:
            continue
        for f in files:
            if f.lower().endswith(".dds"):
                src = os.path.join(root, f)
                dst = os.path.join(temp_dir, f)
                if not os.path.exists(dst):
                    try:
                        shutil.copy2(src, dst)
                        count += 1
                    except:
                        pass
    return count
