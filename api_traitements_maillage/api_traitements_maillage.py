bl_info = {
    "name": "Prototype API CGAL.",
    "author": "Richard Leestmans",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "description": "Prototype d'API permettant d'éxécuter divers algorithmes provenant de CGAL.",
    "location": "VIEW3D > UI > API C++",
    "doc_url": "",
    "tracker_url": "",
    "category": "Mesh",
}

import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper
import bmesh
from mathutils import Vector, Color
import numpy as np
import json
import os
from api_modules.algorithms_api import Router
from api_modules.py_mesh import PyMeshApi
import time
import sys
import subprocess
import platform
import pymeshlab

# Fonction d'affichage des différentes propriétés suivant l'algorithme choisi par l'utilisateur
def draw_properties(layout, context, algorithm_name):
    # Récupération de la classe de propriétés associée à l'algorithme sélectionné
    algorithm_properties = getattr(context.scene, algorithm_name.lower(), None)
    if algorithm_properties is not None:
        col = layout.column(align=True)
        col.scale_y = 1.4
        # affichage des propriétés de l'algorithme
        for prop_attribute in Globals.algorithm_properties[algorithm_name.lower()][1].keys():
            col.prop(algorithm_properties, prop_attribute)
    else:
        pass
    # Ajout des boutons d'importation et d'exportation des configurations prédéfinies
    row = layout.row(align=True)
    row.scale_y = 1.4
    col = row.column(align=True)
    col.operator(VIEW3D_OT_load_configuration.bl_idname, text="Importer")
    if algorithm_properties is not None:
        col = row.column(align=True)
        col.enabled = is_option_selected(context, algorithm_name)
        col.operator(VIEW3D_OT_save_configuration.bl_idname, text="Sauvegarder")
    else:
        pass

    # Ajout d'un bouton permettant à l'utilisateur de réinitialiser les valeurs des paramètres de l'algorithme courant
    if algorithm_properties is not None:
        row = layout.row()
        row.scale_y = 1.2
        row.operator(VIEW3D_OT_set_properties_to_default.bl_idname, text="Réinitialiser les paramètres de l'algorithme")
    else:
        pass

    
## Fonctions d'applications des traitements sur le maillage courant à partir des résultats retournés par l'algorithme choisi par l'utilisateur
def display_results(context, data, output_result):
    # Stockage du message de résultats dans la propriété permettant d'afficher des messages dans l'API
    context.scene.api_properties.result_infos = data.get("result_infos", "")

def set_new_mesh(context, data, output_result):
    # Récupération de l'objet courant
    object = context.active_object

    # Récupération de toutes les transformations appliquées à l'objet courant (translation, rotation, mise à l'échelle)
    translation = object.location.copy()
    rotation = object.rotation_euler.copy()
    scale = object.scale.copy()

    # ainsi que le nom du maillage
    mesh_name = object.data.name

    # extraction des données de la structure (ici les nouvelles coordonnées des sommets restants du maillage ainsi que les nouveaux indices des faces)
    resulting_mesh_vertices = data.get("vertices", None)
    resulting_mesh_faces = data.get("faces", None)

    if resulting_mesh_vertices is not None and resulting_mesh_faces is not None:
        # Déselection de tous les objets de la scène
        bpy.ops.object.select_all(action="DESELECT")
        # Vérification si l'algorithme nécessite le remplacement du maillage courant par le nouveau maillage
        if output_result == "replace_mesh":
            # Sélection de l'objet à modifier
            object.select_set(True)    
            # Suppression de l'ancien maillage
            bpy.ops.object.delete()
        else:
            pass

        # Création d'un nouveau maillage
        resulting_mesh = bpy.data.meshes.new(name=mesh_name)
        # et construction de ce dernier avec les nouvelles données
        # resulting_mesh.from_pydata(resulting_mesh_vertices, resulting_mesh_edges, resulting_mesh_faces)
        resulting_mesh.vertices.add(len(resulting_mesh_vertices) // 3)
        resulting_mesh.vertices.foreach_set("co", resulting_mesh_vertices)
        
        total_face_indices = len(resulting_mesh_faces)
        resulting_mesh.loops.add(total_face_indices)
        resulting_mesh.polygons.add(total_face_indices // 3)
    
        resulting_mesh.loops.foreach_set("vertex_index", resulting_mesh_faces) 
        
        loop_start = [i * 3 for i in range(total_face_indices // 3)]
        loop_total = [3] * (total_face_indices // 3)
        
        resulting_mesh.polygons.foreach_set("loop_start", loop_start) 
        resulting_mesh.polygons.foreach_set("loop_total", loop_total)
        resulting_mesh.polygons.foreach_set("use_smooth", [0] * (total_face_indices // 3))

        # mise à jour du maillage avec sa nouvelle structure
        resulting_mesh.update()
        resulting_mesh.validate()
        
        # Création d'un objet Blender auquel associer le maillage nouvellement créé
        obj = bpy.data.objects.new(mesh_name, resulting_mesh)

        # Application de l'ensemble des transformations de l'ancien maillage sur le nouveau
        obj.location = translation
        obj.rotation_euler = rotation
        obj.scale = scale

        # Ajout de l'objet à la scène
        bpy.context.scene.collection.objects.link(obj)

        # et sélection de l'objet dans la scène 3D comme nouvel objet courant
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        # Et nous centrons la scène sur le nouvel objet créé (équivaut à Numpad .)
        bpy.ops.view3d.view_selected(use_all_regions=False)
    else:
        raise RuntimeError("Une erreur s'est produite lors de la création du nouveau maillage.")


def set_mesh_colors(context, data, output_result):
    # Récupération de l'objet courant
    object = context.active_object
    # et de son maillage associé
    mesh = object.data
    
    # Récupération du tableau des couleurs du maillage
    colors = data.get("colors", None)
    # Récupération du nombre de segments obtenus
    # colors_number = data.get("colors_number", None)
    if colors is not None:
        # Récupération du nom de l'algorithme choisi par l'utilisateur
        current_algorithm_name = context.scene.api_properties.algorithm_choice.lower()

        # Récupération du groupe de propriétés associé à l'algorithme courant
        property_group = getattr(context.scene, current_algorithm_name, None)

        # Récupération si présente, l'option permettant de supprimer les matériaux déjà associés au maillage courant
        delete_materials_option = getattr(property_group, "delete_materials", None)
        # Vérification si l'utilisateur a souhaité supprimer les matériaux déjà associés au maillage
        if delete_materials_option is not None and delete_materials_option:
            mesh.materials.clear()
            attributes = mesh.attributes
            for i in range(len(attributes) - 1, -1, -1):
                name = attributes[i].name
                if name.split('.')[0] == "Face_Col" or name.split('.')[0] == "Vertex_Col":
                    attributes.remove(attributes[i])
        else:
            pass

        # Création de l'attribut de couleurs (vertex color layout) permettant de gérer les couleurs des faces ou des sommets du maillage
        if output_result == "face_coloration":
            color_layout = mesh.attributes.new(name="Face_Col", type="FLOAT_COLOR", domain="FACE")
        elif output_result == "vertex_coloration":
            color_layout = mesh.color_attributes.new(name="Vertex_Col", type="FLOAT_COLOR", domain="POINT")
            # définition de l'attribut comme attribut de couleurs actif
            setattr(mesh.color_attributes, "active_color", color_layout)
        else:
            raise RuntimeError("Le choix de sortie est inconnu.")

        # Stockage des informations de couleurs dans l'attribut
        color_layout.data.foreach_set("color", colors)

        # Récupération du nombre de matériaux déjà associés au maillage (servira d'offset pour affecter le bon matériau à la bonne face)
        nb_materials = len(mesh.materials)

        # Création d'un nouveau matériau permettant d'afficher les couleurs du maillage
        material = bpy.data.materials.new(name="Mesh_Color")

        # affectation du nouveau matériau au maillage
        mesh.materials.append(material)
        # utilisation des noeuds pour ce matériau
        material.use_nodes = True

        # Récupération de l'ensemble des noeuds du matériau et de l'ensemble des liens inter-noeuds
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # Création d'un noeud "Attribut"
        attribute = nodes.new(type="ShaderNodeAttribute")
        # définition du nom de l'attribut sur "Face_Col" (couleurs des faces du maillage) ou "Vertex_Col" (couleurs des sommets du maillage)
        attribute.attribute_name = color_layout.name
        attribute.location = (60, 330)

        # Récupération du noeud "Principled BSDF" (présent par défaut)
        bsdf = nodes["Principled BSDF"]
        # Création d'un lien entre la sortie "Color" du noeud "Attribut" et l'entrée "Base Color" du noeud "Principled BSDF"
        links.new(bsdf.inputs["Base Color"], attribute.outputs["Color"])

        # Désélection de tous les noeuds présents dans le matériau
        for node in nodes:
            node.select = False

        # Affectation de l'indice du matériau nouvellement créé à toutes les faces du maillage
        mesh.polygons.foreach_set("material_index", [nb_materials] * len(mesh.polygons))
        # Définition de l'attribut créé comme attribut actif du maillage
        mesh.update()

        # Passage du mode de rendu sur "MATERIAL" afin de pouvoir visualiser le résultat
        context.space_data.shading.type = "MATERIAL"
    else:
        raise RuntimeError("Une erreur s'est produite lors de l'affectation des couleurs aux faces du maillage.")


## Fonctions de fabrication des propriétés Blender
# Création d'une IntProperty à la volée
def create_integer_property(data):
    default_value = data.get("default", 0)
    return bpy.props.IntProperty(name=data.get("name", ""),
        description=data.get("description", ""),
        default=default_value,  # Valeur par défaut
        min=data.get("min", 0),  # Valeur minimale
        max=data.get("max", 1),  # Valeur maximale
        step=data.get("step", 1)), default_value  # Incrémentation pour le curseur


# Création d'une FloatProperty à la volée
def create_float_property(data):
    default_value = data.get("default", 0)
    return bpy.props.FloatProperty(name=data.get("name", ""),
        description=data.get("description", ""),
        default=default_value,  # Valeur par défaut
        min=data.get("min", 0),  # Valeur minimale
        max=data.get("max", 1),  # Valeur maximale
        step=data.get("step", 1)), default_value  # Incrémentation pour le curseur (une valeur "step" de 1 pour une FloatProperty indique un pas de 0.01)


# Création d'une BoolProperty à la volée
def create_boolean_property(data):
    default_value = True if data.get("default", "") == "true" else False
    return bpy.props.BoolProperty(name=data.get("name", ""),
        description=data.get("description", ""),
        default=default_value), default_value  # Valeur par défaut


# Création d'une EnumProperty à la volée
def create_enum_property(data):
    # Récupération des données des items de la liste déroulante
    items_data = data["items"]
    # Création d'une liste contenant le choix par défaut de la liste déroulante
    items = [("DEFAULT", "--Choix de l'option--", "")]
    # Remplissage de la liste avec toutes les options de sortie disponibles pour cet algorithme
    for item in items_data:
        items.append((item["id"], item["name"], item.get("description", "")))
    return bpy.props.EnumProperty(name=data.get("name", ""),
        items=items, 
        default="DEFAULT"), "DEFAULT"


# Création d'une FloatVectorProperty à la volée
def create_float_vector_property(data):
    default_value = tuple(data.get("default", [0,0,0]))
    return bpy.props.FloatVectorProperty(name=data.get("name", ""),
        description=data.get("description",""),
        default=default_value,  # Valeur par défaut
        min=data.get("min", 0),  # Valeur minimale
        max=data.get("max", 1),  # Valeur maximale
        subtype=data.get("subtype","none").upper()), default_value


## Fonctions de préparation du maillage et de collecte des données à envoyer aux algorithmes côté C++
# Fonction permettant de triangulariser un maillage en mode "OBJET"
def triangulate_mesh(object, data):
    # Récupération du maillage associé à l'objet courant
    mesh = object.data
    # Création d'un bmesh qui va contenir une copie virtuelle de notre maillage et sur lequel va s"appliquer la triangularisation des faces
    bm = bmesh.new()
    bm.from_mesh(mesh)
        
    # Vérification que le maillage ne possède pas de doublons en supprimant les sommets qui se superposent
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0001)
    # puis triangularisation des faces de la copie virtuelle du maillage
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    
    # Mise à jour du maillage courant en écrasant ses anciennes données par celles contenues dans la copie virtuelle
    bm.to_mesh(mesh)
    # et suppression de la copie virtuelle
    bm.free()


def get_vertex_coordinates(object, data):
    # Récupération du maillage associé à l'objet courant
    mesh = object.data
    # Récupération des coordonnées des sommets du maillage
    vertices = np.zeros(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", vertices)
    # et stockage du résultat dans le dictionnaire des données à envoyer
    data["vertices"] = vertices


def get_face_indices(object, data):
    # Récupération du maillage associé à l'objet courant
    mesh = object.data
    # Récupération des indices des faces du maillage
    faces = np.zeros(len(mesh.polygons) * 3, dtype=np.int32)
    mesh.polygons.foreach_get("vertices", faces)
    # et stockage du résultat dans le dictionnaire des données à envoyer
    data["faces"] = faces


def get_color_data(object, data):
    # Récupération du maillage associé à l'objet courant
    mesh = object.data
    # Récupération de l'attribut de couleurs associé aux sommets actif (si présent)
    active_vertex_colors = mesh.color_attributes.active_color
    # S'il existe un attribut de couleurs associé aux sommets du maillage
    if active_vertex_colors:
        # Création d'un tableau numpy permettant de stocker les couleurs du maillage
        vertex_color_array = np.zeros(len(mesh.vertices) * 4, dtype=np.float64)
        # Stockage des couleurs de l'attribut dans le tableau numpy
        active_vertex_colors.data.foreach_get("color", vertex_color_array)
        data["vertex_color"] = vertex_color_array
    # S'il n'y a pas d'attributs associant des couleurs aux sommets du maillage, nous essayons de voir
    # s'il existe un attribut associant des couleurs aux faces du maillage
    else:
        # Récupération des attributs du maillage
        attributes = mesh.attributes
        # Parcours des attributs du dernier au premier de sorte à récupérer le dernier attribut créé associant
        # des couleurs aux faces (si présent)
        for i in range(len(attributes) - 1, -1, -1):
            # Si l'attribut courant contient des couleurs (données de type FLOAT_COLOR) et les associe aux faces
            # alors il s'agit de l'attribut recherché
            current_attribute = attributes[i]
            if current_attribute.data_type == "FLOAT_COLOR" and current_attribute.domain == "FACE":
                # Création d'un tableau numpy permettant de stocker les informations des couleurs
                face_color_array = np.zeros(len(mesh.polygons) * 4, dtype=np.float64)
                current_attribute.data.foreach_get("color", face_color_array)
                data["face_color"] = face_color_array
                break
            else:
                pass


## Fonctions permettant de transformer des types de données de Blender en types de données MeshLab
def get_percentage_value_instance(value):
    return pymeshlab.PercentageValue(value)


def get_pure_value_instance(value):
    return pymeshlab.PureValue(value)


def get_color_instance(value):
    return pymeshlab.Color(round(value.r * 255), round(value.g * 255), round(value.b * 255))


def get_numpy_float_array(value):
    return np.array(value, dtype=np.float64)


# Variables globales
class Globals:
    # Fabrique à création de propriétés Blender
    properties_factory = {"integer": create_integer_property,
                         "float": create_float_property,
                         "boolean": create_boolean_property,
                         "enum": create_enum_property,
                         "percentage_value": create_float_property,
                         "pure_value": create_float_property,
                         "color": create_float_vector_property,
                         "float_array": create_float_vector_property}
    # Fabrique à préparation du maillage et des données à envoyer côté C++
    inputs_factory = {"triangulation": triangulate_mesh,
                      "vertex_coordinates": get_vertex_coordinates,
                      "face_indices": get_face_indices,
                      "color_data": get_color_data}
    # Table permettant de gérer les résultats retournés par l'API C++ et d'effectuer les traitements correspondants en fonction
    # de la nature de la demande initiale de retour des données
    outputs_table = {"message": display_results, # Affiche un message dans l'API donnant des informations sur les résultats du traitement effectué
                     "face_coloration": set_mesh_colors, # Définit des nouvelles couleurs pour les faces du maillage
                     "vertex_coloration": set_mesh_colors, # Définit des nouvelles couleurs pour les sommets du maillage
                     "replace_mesh": set_new_mesh, # Remplace le maillage sélectionné par un nouveau maillage
                     "add_mesh": set_new_mesh} # Ajoute le maillage créé dans la scène sans supprimer le maillage sélectionné
    # Table permettant d'associer à un attribut (présent sous la forme d'un string) une classe de propriétés (héritant de PropertyGroup) que l'attribut
    # référencera à l'aide d'un PointerProperty. Exemple : 'segmentation_cgal' : CgalSegmentationProperties
    # Est utilisée retirer les classes de propriétés du registre de Blender et de supprimer les références à ces dernières par un objet de Blender lors de l'appel de la fonction "unregister"
    properties_table = {}
    # Table associant à chaque algorithme une liste contenant l'identifiant du langage de programmation de l'algorithme ainsi que la liste éventuelle de ses propriétes sous forme de dictionnaire et le nom de la function utilisée pour réaliser l'algorithme (cas de MeshLab). 
    # Exemples : "segmentation_cgal" : [0, {"clusters" : 4, "smoothness" : 0.5, "output_options" : "DEFAULT", "delete_materials" : False}, ["integer", "float", "enum", "boolean"], []]
    #            "colorize_curvature_apss" : [1, {"filterscale" : 2, "projectionaccuracy" : 0.01, "maxprojectioniters" : 15, "sphericalparameter" : 1, "curvaturetype" : "DEFAULT", "delete_materials" : False}, ["float", "float", "integer", "float", "enum", "boolean"], ["compute_curvature_and_color_apss_per_vertex"]]
    algorithm_properties = {}
    # Table associant au nouveau d'un algorithme une liste contenant le nombre d'étapes de l'algorithme (comprendre le nombre de sous-algorithmes utilisés) ainsi que la liste des n indices des sous-algorithmes dans lesquels les m paramètres sont présents
    # -1 indique que le paramètre n'est pas présent dans un sous-algorithme sinon une valeur d'indice j à la position i dans la liste indique que le i-ème paramètre est présent dans le j-ème sous-algorithme
    # Exemples : "segmentation_cgal" : [1, [1,1,-1,-1]]
    #            "colorize_curvature_apss" : [1, [1,1,1,1,1,-1]]
    algorithm_steps = {}
    # Table associant à chaque algorithme la liste des opérations à effectuer avant d'envoyer les données côté C++ (traitement prélable du maillage, informations du maillage à récupérer, ...)
    # Exemple : "segmentation_cgal' : ["triangulation", "vertex_coordinates", "face_indices"]
    algorithm_input_pipeline = {}
    # Table associant à chaque algorithme de l'API sa description associée
    algorithm_description = {}
    # Dernière configuration chargée par l'utilisateur
    last_loaded_configuration = {}
    # Table permettant de convertir les valeurs des propriétés Blender vers des types MeshLab
    meshlab_types = {"percentage_value": get_percentage_value_instance,
                     "pure_value": get_pure_value_instance,
                     "color": get_color_instance,
                     "float_array": get_numpy_float_array}


def create_description(content):
    # Définition du maximum de caractères à afficher dans l'info-bulle de l'algorithme
    max_length = 300
    # Définition du maximum de caractères à afficher par ligne (3 lignes en tout)
    max_row_length = 60
    # Séparation des mots de la description de l'algorithme
    words = content.split(" ")
    lines = []
    current_line = ""
    # Création d'un compteur sur le nombre de lignes extraites
    i = 0
    # Ainsi qu"un compteur sur le nombre de mots lus dans la description
    word_count = 0
    while i < (max_length/max_row_length) and word_count < len(words):
        # Récupération du mot courant
        word = words[word_count]
        line_length = len(current_line) + len(word) + 1
        # Si la somme des caractères de la ligne courante + la longueur du mot courant ne dépasse pas max_row_length
        if line_length <= max_row_length:
            # ajout du mot à la ligne courante
            current_line += (word + " ")
        else:
            # Sinon ajout de la ligne courante dans la liste des lignes de la description
            lines.append(current_line.strip())
            i += 1
            # et ajout du mot courant dans la prochaine ligne
            current_line = word + " "
        # mise à jour du compteur sur les mots lus
        word_count += 1
    # Si la description fait plus de 180 caractères
    lines.append(current_line.strip())
    i += 1
    if i >= (max_length / max_row_length):        
        # ajout de "..." à la fin de la dernière ligne de la description
        lines[-1] = lines[-1][:-3] + "..."
    return lines

    
# Fonctions d'exécution et d'application des traitements sur le maillage courant
def compute_algorithm(context):
     # Récupération de l'objet courant
    object = context.active_object
    if not object or object.type != "MESH":
        raise RuntimeError("Aucun maillage n'est sélectionné")
    else:
        # Passage du contexte en mode "OBJET"
        bpy.ops.object.mode_set(mode="OBJECT")
        # et du mode de rendu à "SOLID"
        context.space_data.shading.type = "SOLID"
        # Préparation du maillage et récupération des données à envoyer à l'algorithme côté C++
        # Récupération de la scène
        scene = context.scene
        # Récupération du groupe de propriétés de l'API Blender
        api_properties = scene.api_properties
        # Suppression du message
        api_properties.result_infos = ""
        # Récupération du nom de l'algorithme sélectionné par l'utilisateur
        algorithm_name = api_properties.algorithm_choice.lower()
        # Création d'un dictionnaire vide qui va contenir l'ensemble des données à envoyer
        data = {}
        # et exécution des différentes opérations pré-envoi des données
        for operation in Globals.algorithm_input_pipeline[algorithm_name]:
            Globals.inputs_factory[operation](object, data)

        # Récupération des données des propriétés de l'algorithme courant
        algorithm_data = Globals.algorithm_properties[algorithm_name]
        # Récupération des étapes de l'algorithme courant
        algorithm_steps = Globals.algorithm_steps[algorithm_name]
        # Ajout du nom de la fonction utilisée pour réaliser l'algorithme (pour MeshLab)
        data["function"] = algorithm_data[3]
        params = [{} for _ in range(algorithm_steps[0])]
        options = {}
        # Récupération du groupe de propriété associé à l'algorithme choisi (si présent)
        # et stockage des valeurs de l'ensemble des proprétés dans le dictionnaire data
        property_group = getattr(scene, algorithm_name, None)
        if property_group is not None:           
            for i, property_name in enumerate(algorithm_data[1].keys()):
                # Si le paramètre n'est pas utilisé dans l'algorithme
                if algorithm_steps[1][i] == -1:
                    options[property_name] = getattr(property_group, property_name)
                else:
                    # Vérification si la valeur n'est pas de type Meshlab
                    if algorithm_data[2][i] not in ["percentage_value", "pure_value", "color", "float_array"]:
                        params[algorithm_steps[1][i] - 1][property_name] = getattr(property_group, property_name)
                    else:
                        params[algorithm_steps[1][i] - 1][property_name] = Globals.meshlab_types[algorithm_data[2][i]](getattr(property_group, property_name))           
        else:
            pass
        data["params"] = params
        data["options"] = options
                    
        
        start = time.time()

        # Instanciation de l'algorithme de traitement de maillage
        # Si l'algorithme provient de la bibliothèque MeshLab
        if algorithm_data[0] == 1:
            algorithm = PyMeshApi(data)
        # Sinon il provient d'une autre bibliothèque
        else:
            algorithm = Router(algorithm_data[0], algorithm_name, data)

        # Exécution ensuite de l'algorithme choisi par l'utilisateur
        try:
            algorithm.init()
        except Exception as err:
            raise err
        
        # Récupération de la structure de données résultante de l'algorithme exécuté avec CGAL côté C++
        results = algorithm.get_result()
        end = time.time()
        print(f"Temps d'exécution de l'algorithme : {end-start}s")
        # gestion des résultats en fonction de la requête initiale de l'utilisateur
        output_results = results.get("output_result", [])
        for output_result in output_results:
            Globals.outputs_table[output_result](context, results, output_result)


def check_required_modules():
    # Vérification que le ou les modules nécessaires à l'extension sont bien installés
    # récupération du chemin absolu vers les modules tiers installés dans Blender
    modules_path = bpy.utils.user_resource("SCRIPTS", path="modules")

    # Si un des modules est manquant
    if not os.path.isdir(os.path.join(modules_path, "pymeshlab")):
        # mise à niveau de pip
        subprocess.run([sys.executable, "-m", "ensurepip", "--user"])
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        # Nous vérifions s'il est bien installé dans l'environnement python de Blender
        # Cas particulier pour Windows, la dernière version installée avec pip install pymeshlab (2023.12.post2)
        # fait planter Blender à l'importation. Donc installation de la version précédente sans les dépendances.
        # numpy est déjà installé dans Blender et il semble qu'il y ait un conflit entre pymeshlab et MSVCP140 causant un plantage
        # du programme notamment lors de l'appel du constructeur Mesh de pymeshlab.
        os_name = os.name
        if os_name == "nt": 
            subprocess.run([sys.executable, "-m", "pip", "install", "pymeshlab==2023.12.post1", "--no-deps", "-t", modules_path])
        elif os_name == "posix" and platform.system() == "Linux":
            subprocess.run([sys.executable, "-m", "pip", "install", "pymeshlab", "-t", modules_path])
        else:
            raise RuntimeError("Votre système d'exploitation n'est pas pris en charge par l'extension.")
        print("Installation des modules requis terminée. Merci de redémarrer Blender pour appliquer les changements...")
    # Sinon le module est déjà installé
    else:
        print("Les modules requis sont déjà installés.")


def load_algorithms():
    # Récupération du chemin absolu d'où le script est exécuté
    script_absolute_path = os.path.dirname(os.path.realpath(__file__))
    # Chargement des données liées à tous les algorithmes contenus dans le fichier "config.json"
    metadata = None
    try:
        with open(os.path.join(script_absolute_path, "config.json")) as f:
            metadata = json.load(f)
    except Exception as e:
        print("Une erreur s'est produite lors de la tentative d'ouverture du fichier 'config.json'.")
        raise e
    
    # Création des items de la liste déroulante permettant à l'utilisateur de choisir quel algorithme appliquer sur son maillage
    algorithm_items = [("DEFAULT", "--Choix de l'algorithme--", "")]

    # Parcours des données du fichier JSON
    for data in metadata.values():
        # Récupération de l'identifiant du langage de programmation courant
        try:
            programming_language = data["language_id"]
        except Exception as e:
            print("Chaque langage de programmation doit posséder son champ 'language'.")
            raise e
        # Récupération de la liste des bibliothèques associées au langage de programmation courant
        libraries = data.get("libraries", None)
        if libraries is not None:
            # Parcours des bibliothèques associées à un langage donné dans le fichier JSON
            for library in libraries:
                # Récupération du nom de la bibliothèque courante
                library_name = library.get("id_name", "")
                # Récupération de la liste des algorithmes associés à la bibliothèque courante
                algorithms = library.get("algorithms", None)
                if algorithms is None:
                    raise RuntimeError(f"La bibliothèque {library_name} ne possède pas de champ 'algorithms'.")
                else:
                    for algorithm in algorithms:
                        # Récupération du nombre de l'algorithme courant
                        algorithm_name = algorithm["id_name"]
                        # Récupération de la description de l'algorithme
                        description = algorithm.get("description", "")
                        # création du choix dans a liste déroulante de l'API
                        algorithm_items.append((algorithm_name.upper(), algorithm["name"], description))
                        # Stockage de la description de l'algorithme pour l'API dans la table algorithm_description de la structure Globals
                        Globals.algorithm_description[algorithm_name] = create_description(description)
                        # récupération de la liste des opérations à effectuer avant d'envoyer les données côté C++
                        Globals.algorithm_input_pipeline[algorithm_name] = algorithm.get("input", [])
                        # Initialisation de la liste dans la table "algorithm_properties" avec le langage de programmation utilisé et qui contiendra le nom des propriétés de l'algorithme courant et leurs valeurs par défaut associées
                        Globals.algorithm_properties[algorithm_name] = [programming_language]
                        # Initialisation de la liste de la table "algorithm_steps" avec le nombre de sous-algorithmes permettant de mener à bien l'exécution de l'algorithme principal
                        Globals.algorithm_steps[algorithm_name] = [algorithm.get("steps")]
                        algorithm_props = Globals.algorithm_properties[algorithm_name]
                        # Initialisation d'un dictionnaire permettant de stocker les propriétés de l'algorithme courant
                        properties_dict = {}
                        # Initialisation d'une liste stockant les types des propriétés de l'algorithme courant
                        properties_types = []
                        # Initialisation d'une liste permettant de stocker si les propriétés de l'algorithme sont utilisées ou non dans l'algorithme et, si oui, dans quel sous-algorithme ce paramètre est utilisé
                        sub_algorithms_parameter = []
                        # Récupération du dictionnaire des propriétés de l'algorithme courant
                        properties = algorithm.get("properties", None)
                        if properties is not None:
                            # Récupération des données des propriétés de l'algorithme
                            properties_data = properties["data"]
                            # Création d'une classe de propriétés vide héritant de PropertyGroup qui englobera l'ensemble des propriétés de l'algorithme courant
                            property_class = type(properties["class_name"], (bpy.types.PropertyGroup,), {})

                            # Enregistrement de la classe dans le registre de Blender
                            bpy.utils.register_class(property_class)
                            # Ajout des différentes propriétés à la classe
                            for property in properties_data:
                                # Création de la propriété
                                property_constructor, default_value = Globals.properties_factory[property["type"]](property["data"])
                                setattr(property_class, property["id_name"], property_constructor)
                                # Association du nom de la propriété courante à sa valeur par défaut dans la table des propriétés
                                properties_dict[property["id_name"]] = default_value
                                # Ajout du type de la propriété dans le conteneur correspondant
                                properties_types.append(property["type"])
                                # Récupération de la valeur permettant de savoir si la propriété courante est utilisée ou non dans l'algorithme et, si oui, dans quel sous-algorithme
                                sub_algorithms_parameter.append(property.get("algorithm_step", -1))                 
                            # Stockage de la classe nouvellement créée dans une table permettant de la désinscrire du registre de Blender lors de l'appel de la fonction "unregister"
                            Globals.properties_table[algorithm_name] = property_class
                            # Ajout du dictionnaire de propriétés dans la table algorithm_properties
                            algorithm_props.append(properties_dict)
                            # Ajout de la liste des types des propriétés dans la table algorithm_properties
                            algorithm_props.append(properties_types)
                            # Ainsi que la liste indiquant si les propriétés précédentes sont utilisées dans l'algorithme
                            Globals.algorithm_steps[algorithm_name].append(sub_algorithms_parameter)
                        
                            # et référencement de la classe par un attribut
                            setattr(bpy.types.Scene, algorithm_name, bpy.props.PointerProperty(type=property_class))
                        else:
                            algorithm_props.append(properties_dict)
                            algorithm_props.append(properties_types)
                            Globals.algorithm_steps[algorithm_name].append(sub_algorithms_parameter)
                        # Ajout de la fonction utilisée pour l'algorithme (cas de MeshLab)
                        algorithm_props.append(algorithm.get("functions_name", []))                   
        else:
            pass

    
    # Création de la classe de propriétés de l'API Blender qui contiendra une liste de choix laissant la possibilité à l'utilisateur
    # soit de choisir un algorithme à appliquer sur un maillage en lui laissant la possibilité de personnaliser ses paramètres, soit d'importer la configuration
    # pré-programmée d'un algorithme contenu dans un fichier au format json, la liste déroulante des algorithmes implémentés
    # ainsi qu'une propriété contenant l'ensemble des messages pouvant être retournés par l'API interne (côté C++)
    # Création de la classe vide
    api_class = type("ApiProperties", (bpy.types.PropertyGroup,), {})

    # Enregistrement de la classe dans le registre de Blender
    bpy.utils.register_class(api_class)
    
    # Stockage de l'énumération matérialisant la liste déroulante et stockant tous les choix d'algorithme
    setattr(api_class, "algorithm_choice", bpy.props.EnumProperty(name="", items=algorithm_items, default="DEFAULT"))
    # ainsi que la propriété gérant les messages
    setattr(api_class, "result_infos", bpy.props.StringProperty(
        name="Résultat",
        description="informations sur le ou les résultats de l'algorithme courant utilisé",
        default=""))
    # tout comme une propriété permettant d'afficher et de masquer la description des algorithmes dans l'API Blender
    setattr(api_class, "description_is_hidden", bpy.props.BoolProperty(name="Afficher/Masquer la description de l'algorithme", default=True))
    # Stockage de la classe nouvellement créée dans une table permettant de la désinscrire du registre de Blender lors de l'appel de la fonction "unregister"
    Globals.properties_table["api_properties"] = api_class
    # Référencement du groupe de propriétés par un objet de Blender (ici la scène)
    bpy.types.Scene.api_properties = bpy.props.PointerProperty(type=api_class)


# Fonction permettant de vérifier si l'utilisateur a choisi une option de sortie pour l'algorithme choisi (seulement si cette option est disponible)
def is_option_selected(context, algorithm_name):
    # Récupération du groupe de propriétés de l'algorithme courant
    property_group = getattr(context.scene, algorithm_name.lower(), None)
    if property_group is not None:
        for property_name in Globals.algorithm_properties[algorithm_name.lower()][1].keys():
            # Récupération du choix de l'option de l'utilisateur pour l'algorithme courant
            if getattr(property_group, property_name) == "DEFAULT":
                return False
            else:
                pass
        return True
    else:
        return True
    

class VIEW3D_OT_execute_algorithm(bpy.types.Operator):
    """Applique l'algorithme choisi sur le maillage sélectionné"""
    bl_idname = "wm.execute_algorithm"
    bl_label = "Exécution de l'algorithme"     
    bl_options = {"REGISTER", "UNDO"} 
    
    def execute(self, context):
        compute_algorithm(context)   
        return {"FINISHED"}


class VIEW3D_OT_display_description(bpy.types.Operator):
    """Etendre ou réduire la description de l'algorithme courant"""
    bl_idname = "wm.display_description"
    bl_label = "Etendre la description"     
    bl_options = {"REGISTER", "UNDO"} 
    
    def switch_visibility(self, context):
        context.scene.api_properties.description_is_hidden = not context.scene.api_properties.description_is_hidden


    def execute(self, context):
        self.switch_visibility(context)  
        return {"FINISHED"}
    

class VIEW3D_OT_load_configuration(bpy.types.Operator, ImportHelper):
    """Charger une configuration prédéfinie d'un algorithme au format JSON"""
    bl_idname = "wm.load_configuration"
    bl_label = "Charger une configuration"     
    bl_options = {"REGISTER", "UNDO"} 

    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={"HIDDEN"},
    )

    def load_configuration(self, context):
        # Récupération de la configuration chargée
        config = Globals.last_loaded_configuration
        # Récupération du nom de l'algorithme utilisé dans la configuration
        algorithm_name = config.get("algorithm", None)
        if algorithm_name is not None:
            setattr(context.scene.api_properties, "algorithm_choice", algorithm_name.upper())
            # Récupération de la classe de propriétés associée à l'algorithme chargé
            algorithm_properties = getattr(context.scene, algorithm_name)
            for property_name, value in config["properties"].items():
                setattr(algorithm_properties, property_name, value)
        else:
            raise RuntimeError("Une erreur s'est produite lors de la lecture du fichier de configuration JSON. Vérifiez que la structure contient bien un champ 'algorithm'.")
        # Nous forçons le rafraichissement de l'interface de l'extension
        context.area.tag_redraw()

    def execute(self, context):
        # Récupération de l'extension du fichier chargé
        file_extension = self.filepath.rsplit('.')[-1].lower()
        if file_extension != "json":
            raise RuntimeError("Le fichier importé doit être au format json.")
        else:
            print(f"Chargement du fichier: {self.filepath}...")
            try:
                with open(self.filepath) as f:
                    Globals.last_loaded_configuration = json.load(f)
                    self.load_configuration(context)
            except Exception as e:
                print(f"Une erreur s'est produite lors de la tentative d'ouverture du fichier {self.filepath}.")
                raise e
            setattr(context.scene.api_properties, "configuration_is_loaded", True)
        return {"FINISHED"}

    def invoke(self, context, event):
        # Ouverture de l'explorateur de fichiers
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    

class VIEW3D_OT_save_configuration(bpy.types.Operator, ExportHelper):
    """Exporter la configuration de l'algorithme courant au format JSON"""
    bl_idname = "wm.export_configuration"
    bl_label = "Exporter cette configuration"     
    bl_options = {"REGISTER", "UNDO"} 

    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={"HIDDEN"},
    )
    filename_ext = ".json"

    def __init__(self):
        self.data = {}

    def get_current_configuration(self, context):
        # Création d'une variable qui contiendra le nom du fichier à exporter
        filename = ""
        # Récupération du nom de l'algorithme courant
        algorithm_name = context.scene.api_properties.algorithm_choice.lower()
        # Ajout du nom de l'algorithme dans le nom du fichier
        filename += algorithm_name + "_"
        # et dans le dictionnaire
        self.data["algorithm"] = algorithm_name
        # Récupération de la classe de propriétés associée à l'algorithme sélectionné
        algorithm_properties = getattr(context.scene, algorithm_name, None)
        if algorithm_properties is not None:
            # Création d'un champ dans le dictionnaire contenant l'ensemble des propriétés de l'algorithme
            self.data["properties"] = {}
            # Création d'une table permettant de remplacer des caractères par d'autres
            translation_table = str.maketrans({'[': '_', ']': '_', '.': '_', ',': '_'})
            # parcours des noms des propriétés associées à l'algorithme courant
            for prop_attribute in Globals.algorithm_properties[algorithm_name][1].keys():
                # Récupération de la valeur associée à la propriété courante
                value = getattr(algorithm_properties, prop_attribute)
                # Si le paramètre est un nombre à virgule, nous l'arrondissons à deux décimales après la virgule
                if isinstance(value, (float,)):
                    result = round(value,2)
                # sinon si le paramètre est de type Vector ou Color (types issus des propriétés XVectorProperty)
                elif isinstance(value, (Color, Vector)):
                    if isinstance(value[0], (float,)):
                        result = [round(value[0],2), round(value[1],2), round(value[2],2)]
                    else:
                        result = [value[0], value[1], value[2]]
                # stockage de la valeur associée au nom de la propriété dans le dictionnaire des données
                self.data["properties"][prop_attribute] = result
                # et mise à jour du nom du fichier
                filename += prop_attribute + "_" + str(result).translate(translation_table) + "_"
        else:
            pass
        return filename[:-1]


    def execute(self, context):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            print(f"Exportation du fichier: {self.filepath} réussie.")
            return {"FINISHED"}
        except Exception as e:
            print(f"Une erreur s'est produite lors de l'exportation du fichier {self.filepath} : {e}.")
            return {"CANCELLED"}        

    def invoke(self, context, event):
        # Récupération du nom du fichier à exporter
        filename = self.get_current_configuration(context)
        self.filepath = filename + self.filename_ext
        # Ouverture du gestionnaire de fichier de Blender
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
    

class VIEW3D_OT_set_properties_to_default(bpy.types.Operator):
    """Réinitialiser les valeurs des propriétés de l'algorithme courant"""
    bl_idname = "wm.set_properties_to_default"
    bl_label = "Réinitialiser les paramètres"     
    bl_options = {"REGISTER", "UNDO"} 

    def reset_properties(self, context):
        # Récupération du nom de l'algorithme courant
        algorithm_name = getattr(context.scene.api_properties, "algorithm_choice").lower()
        # Récupération de la classe de propriétés associées à l'algorithme courant
        algorithm_properties = getattr(context.scene, algorithm_name, None)
        if algorithm_properties is not None:
            # Pracours du nom des propriétés et des valeurs par défaut de l'algorithme courant
            for property_name, default_value in Globals.algorithm_properties[algorithm_name][1].items():
                # remise de la valeur de la propriété courante par défaut
                setattr(algorithm_properties, property_name, default_value)
        else:
            pass


    def execute(self, context):
        self.reset_properties(context)
        return {"FINISHED"}

class VIEW3D_OT_align_camera_to_view(bpy.types.Operator):
    """Aligne la vue de la caméra sur la vue de la scène"""
    bl_idname = "wm.camera_to_scene_view"
    bl_label = "Aligner la vue caméra sur la vue de la scène"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bpy.ops.view3d.camera_to_view.poll()

    def execute(self, context):
        # alignement de la vue caméra sur la vue de la scène
        bpy.ops.view3d.camera_to_view()
        return {'FINISHED'}         


class VIEW3D_PT_stereoscopy_panel(bpy.types.Panel):
    bl_label = "Stéréoscopie"  # Titre du panneau latéral
    bl_idname = "VIEW3D_PT_stereoscopy_panel"
    bl_space_type = "VIEW_3D"  # espace dans lequel est situé le panneau
    bl_region_type = "UI"  # région dans laquelle le panneau se situe

    bl_category = "API C++"  # Nom de l'onglet auquel attacher le panneau

    def draw(self, context):
        # Récupération de la scène
        scene = context.scene
        layout = self.layout
        layout.use_property_split = False

        row = layout.row()
        row.scale_y = 1.4
        row.prop(scene.render, "use_multiview", text="Activer la stéréoscopie ?")
        # Si l'utilisateur a choisi d'activer la stéréoscopie
        if scene.render.use_multiview is True:
            # Récupération des propriétés gérant les zones de clipping de la scène
            space_data = context.space_data
            row = layout.row()
            row.scale_y = 1.4
            col = row.column(align=True)
            col.prop(space_data, "clip_start", text="Début du clipping (Scène)")
            col.prop(space_data, "clip_end", text="Fin du clipping (Scène)")
            col = layout.column(align=True)
            col.scale_y = 1.4
            col.prop(scene, "camera")
            # Récupération de la référence contenue dans la propriété scene.camera
            camera = scene.camera
            # Si une caméra est sélectionnée
            if camera is not None:
                # Affichage des zones de clipping de la caméra courante
                col.prop(camera.data, "clip_start", text="Début du clipping (Caméra)")
                col.prop(camera.data, "clip_end", text="Fin du clipping (Caméra)")
                # Affichage des options de la stéréoscopie de la caméra
                col.prop(camera.data.stereo, "convergence_distance", text="Distance du plan de convergence")
                col.prop(camera.data.stereo, "interocular_distance", text="Distance interoculaire")
                col.prop(space_data, "lock_camera", text="Utiliser la vue caméra comme vue de la scène ?")
                row = layout.row()
                row.scale_y = 1.7
                row.operator(VIEW3D_OT_align_camera_to_view.bl_idname, text="Aligner la vue caméra sur la vue de la scène")


class VIEW3D_PT_cpp_api_panel(bpy.types.Panel):
    bl_label = "Algorithmes de traitements de maillages"  # Titre du panneau latéral
    bl_idname = "VIEW3D_PT_cpp_api_panel"
    bl_space_type = "VIEW_3D"  # espace dans lequel est situé le panneau
    bl_region_type = "UI"  # région dans laquelle le panneau se situe

    bl_category = "API C++"  # Nom de l'onglet auquel attacher le panneau

    def draw(self, context):
        # Récupération du groupe de propriétés de l'API
        api_properties = context.scene.api_properties
        layout = self.layout
        layout.use_property_split = False

        row = layout.row()
        row.label(text="Choisissez un algorithme à appliquer sur le maillage courant :")
        row = layout.row()
        row.scale_y = 1.4
        row.prop(api_properties, "algorithm_choice")
        
        # affichage des propriétés en fonction de l'algorithme choisi par l'utilisateur
        # Récupération du nom de l'algorithme courant (provenant soit d'une configuration prédéfinie soit d'un choix de l'utilisateur)
        algorithm_name = api_properties.algorithm_choice
        # Globals.algorithm_properties[current_choice.algorithm_choice]["drawing_properties"](layout, context)
        # création d'une nouvelle ligne dans laquelle nous ajoutons un bouton (instance de la classe VIEW3D_OT_api_cgal)
        if algorithm_name != "DEFAULT":
            draw_properties(layout, context, algorithm_name)
            # Récupération de la description de l'algorithme
            description = Globals.algorithm_description[algorithm_name.lower()]
            row = layout.row()
            row.label(text="Description de l'algorithme :", icon="QUESTION")
            box = layout.box()
            col = box.column()
            # Récupération du booléen gérant l'affichage ou le masquage partiel de la description de l'algorithme
            description_is_hidden = api_properties.description_is_hidden                 
            if description_is_hidden:
                col.label(text=description[0][:-3] + "...")
            else:
                for line in description:
                    col.label(text=line)
            row = box.row()
            row.scale_y = 1.2
            row.operator(VIEW3D_OT_display_description.bl_idname, text="Etendre la description" if description_is_hidden else "Réduire la description")

            if api_properties.result_infos != "":
                for line in api_properties.result_infos.splitlines():
                    layout.label(text=line)
            else:
                pass
            row = layout.row()
            row.enabled = is_option_selected(context, algorithm_name)
            row.scale_y = 1.7
            # l'opérateur est référencé par un nom correspondant à la valeur de l'attribut bl_idname de la classe
            row.operator(VIEW3D_OT_execute_algorithm.bl_idname, text="Appliquer l'algorithme")
        else:
            pass



## Fonctions d'enregistrement, de désincription et de référencement des groupe de propriétés des classes de l'API
classes = (VIEW3D_PT_stereoscopy_panel, VIEW3D_PT_cpp_api_panel, VIEW3D_OT_align_camera_to_view, VIEW3D_OT_set_properties_to_default, VIEW3D_OT_load_configuration, VIEW3D_OT_save_configuration, VIEW3D_OT_display_description, VIEW3D_OT_execute_algorithm)

def algorithm_properties_registering():
    # Enregistrement toutes les classes de propriétés des algorithmes de l'API
    for property_class in Globals.properties_table.values():
        bpy.utils.register_class(property_class)


def unregister_algorithm_properties():
    # Désinscription des classes de propriétés des algorithmes de l'API
    for property_class in reversed(list(Globals.properties_table.values())):
        bpy.utils.unregister_class(property_class)


def create_property_pointers():
    # et pour tous les algorithmes présents dans l'API
    for attribute, property_class in Globals.properties_table.items():
        setattr(bpy.types.Scene, attribute, bpy.props.PointerProperty(type=property_class))


def delete_property_pointers():
    # ainsi que les attributs référençant toutes les classes de propriétés des algorithmes présents dans Blender
    for attribute in Globals.properties_table.keys():
        delattr(bpy.types.Scene, attribute)


def register():
    check_required_modules()
    # Enregistrement des classes basiques (panneau, boutons, ...) dans le registre de Blender
    for cls in classes:
        bpy.utils.register_class(cls)
    load_algorithms()
    # Enregistrement des classes de propriétés des différents algorithmes de l'API ainsi que la liste déroulante
    # algorithm_properties_registering()
    # Création des pointeurs permettant de référencer les propriétés des algorithmes de l'API dans le registre de Blender
    # create_property_pointers()


def unregister():
    # Désinscription des classes de propriétés des algorithmes de l'API
    unregister_algorithm_properties()
    # Désinscription de la liste déroulante
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    # Suppression des pointeurs référençant les propriétés des algorithmes de l'API
    delete_property_pointers()


if __name__ == "__main__":
    register()
