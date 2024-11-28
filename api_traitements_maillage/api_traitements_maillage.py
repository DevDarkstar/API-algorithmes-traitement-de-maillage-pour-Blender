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
import bmesh
import numpy as np
import random
import json
import os
from algorithms_api import Router
import time

# Fonction d'affichage des différentes propriétés suivant l'algorithme choisi par l'utilisateur
def draw_properties(layout, context, algorithm_name):
    if algorithm_name != "DEFAULT":
        # Récupération de la classe de propriétés associée à l'algorithme sélectionné
        algorithm_properties = getattr(context.scene, algorithm_name.lower(), None)
        if algorithm_properties is not None:
            # Création d'un layout de type "box" dans lequel nous allons afficher nos propriétés
            box = layout.box()
            # affichage des propriétés de l'algorithme
            for prop_attribute in Globals.algorithm_properties_name[algorithm_name.lower()]:
                row = box.row()
                row.scale_y = 1.4
                row.prop(algorithm_properties, prop_attribute)
        else:
            pass
    else:
        pass

    
## Fonctions d'applications des traitements sur le maillage courant à partir des résultats retournés par l'algorithme choisi par l'utilisateur
def display_results(context, data):
    # Stockage du message de résultats dans la propriété permettant d'afficher des messages dans l'API
    context.scene.api_properties.result_infos = data.get("result_infos", "")

def set_new_mesh(context, data):
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
        # et sélection de l'objet à modifier
        object.select_set(True)    
        # Suppression de l'ancien maillage
        bpy.ops.object.delete()

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
    else:
        raise RuntimeError("Une erreur s'est produite lors de la création du nouveau maillage.")


def set_face_colors(context, data):
    # Récupération de l'objet courant
    object = context.active_object
    # et de son maillage associé
    mesh = object.data
    
    # Récupération du tableau des identifiants des segments obtenus
    colors = data.get("colors", None)
    # Récupération du nombre de segments obtenus
    colors_number = data.get("colors_number", None)
    if colors is not None and colors_number is not None:
        # Récupération du nom de l'algorithme choisi par l'utilisateur
        current_algorithm_name = context.scene.api_properties.algorithm_choice.lower()

        # Récupération du groupe de propriétés associé à l'algorithme courant
        property_group = getattr(context.scene, current_algorithm_name, None)

        # Vérification si l'utilisateur a souhaité supprimer les matériaux déjà associés au maillage
        if property_group.delete_materials:
            mesh.materials.clear()

        # Récupération du nombre de matériaux déjà associés au maillage (servira d'offset pour affecter le bon matériau à la bonne face)
        nb_materials = len(mesh.materials)

        # Création des matériaux en fonction du nombre de segments
        for _ in range(colors_number):
            # Création d'une couleur aléatoire
            red = random.random()
            green = random.random()
            blue = random.random()

            color = (red, green, blue, 1.0)

            material = bpy.data.materials.new(name="Material")

            # Définition de la couleur du matériau
            material.diffuse_color = color

            # affectation du nouveau matériau au maillage
            mesh.materials.append(material)
        
        # Parcours des faces du maillage et affectation du matériau correspondant à l'indice du segment obtenu
        for face, id in zip(mesh.polygons, colors):
            face.material_index = id + nb_materials 
    else:
        raise RuntimeError("Une erreur s'est produite lors de l'affectation des couleurs aux faces du maillage.")


## Fonctions de fabrication des propriétés Blender
# Création d'une IntProperty à la volée
def create_integer_property(data):
    return bpy.props.IntProperty(name=data.get("name", ""),
        description=data.get("description", ""),
        default=data.get("default", 0),  # Valeur par défaut
        min=data.get("min", 0),  # Valeur minimale
        max=data.get("max", 1),  # Valeur maximale
        step=data.get("step", 1))  # Incrémentation pour le curseur


# Création d'une FloatProperty à la volée
def create_float_property(data):
    return bpy.props.FloatProperty(name=data.get("name", ""),
        description=data.get("description", ""),
        default=data.get("default", 0),  # Valeur par défaut
        min=data.get("min", 0),  # Valeur minimale
        max=data.get("max", 1),  # Valeur maximale
        step=data.get("step", 5))  # Incrémentation pour le curseur (une valeur "step" de 5 pour une FloatProperty indique un pas de 0.05)


# Création d'une BoolProperty à la volée
def create_boolean_property(data):
    return bpy.props.BoolProperty(name=data.get("name", ""),
        description=data.get("description", ""),
        default=True if data.get("default", "") == "true" else False)  # Valeur par défaut


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
        default="DEFAULT")


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
    vertices = np.zeros(len(mesh.vertices) * 3, dtype=np.float32)
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


# Variables globales
class Globals:
    # algorithm_properties = {"DEFAULT" : {"drawing_properties" : draw_default, "input" : None, "output": None},
                          # "SEGMENTATION" : {"drawing_properties" : draw_segmentation_properties, "input" : send_mesh, "output" : set_new_colors},
                          # "SIMPLIFICATION" : {"drawing_properties" : draw_simplification_properties, "input" : send_mesh, "output" : create_new_mesh}}
    # Fabrique à création de propriétés Blender
    properties_factory = {"integer": create_integer_property,
                         "float": create_float_property,
                         "boolean": create_boolean_property,
                         "enum": create_enum_property}
    # Fabrique à préparation du maillage et des données à envoyer côté C++
    inputs_factory = {"triangulation": triangulate_mesh,
                      "vertex_coordinates": get_vertex_coordinates,
                      "face_indices": get_face_indices}
    # Table permettant de gérer les résultats retournés par l'API C++ et d'effectuer les traitements correspondants en fonction
    # de la nature de la demande initiale de retour des données
    outputs_table = {"message": display_results, # Affiche un message dans l'API donnant des informations sur les résultats du traitement effectué
                     "faces_coloration": set_face_colors, # Définit des nouvelles couleurs pour les faces du maillage
                     "new_mesh": set_new_mesh} # Crée un nouveau maillage
    # Table permettant d'associer à un attribut (présent sous la forme d'un string) une classe de propriétés (héritant de PropertyGroup) que l'attribut
    # référencera à l'aide d'un PointerProperty. Exemple : "segmentation_cgal' : CgalSegmentationProperties
    # Est utilisée retirer les classes de propriétés du registre de Blender et de supprimer les références à ces dernières par un objet de Blender lors de l'appel de la fonction "unregister"
    properties_table = {}
    # Table associant à chaque algorithme la liste des noms de ses propriétés sous la forme d'un tuple. 
    # Exemple : "segmentation_cgal' : ("clusters", "smoothness", "output_options", "delete_materials")
    algorithm_properties_name = {}
    # Table associant à chaque algorithme la liste des opérations à effectuer avant d'envoyer les données côté C++ (traitement prélable du maillage, informations du maillage à récupérer, ...)
    # Exemple : "segmentation_cgal' : ["triangulation", "vertex_coordinates", "face_indices"]
    algorithm_input_pipeline = {}
    # Table associant à chaque algorithme de l'API sa description associée
    algorithm_description = {}


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
        # Récupération du groupe de propriété associé à l'algorithme choisi (si présent)
        # et stockage des valeurs de l'ensemble des proprétés dans le dictionnaire data
        property_group = getattr(scene, algorithm_name, None)
        if property_group is not None:
            for property_name in Globals.algorithm_properties_name[algorithm_name]:
                data[property_name] = getattr(property_group, property_name)
        
        start = time.time()
        # Instanciation de l'algorithme de traitement de maillage côté C++
        algorithm = Router(algorithm_name, data)

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
        Globals.outputs_table[results.get("output_result")](context, results)


def load_algorithms():
    print(os.getcwd())
    # Chargement des données liées à tous les algorithmes contenus dans le fichier "config.json"
    metadata = None
    try:
        with open("config.json") as f:
            metadata = json.load(f)
    except Exception as e:
        print("Une erreur s'est produite lors de la tentative d'ouverture du fichier 'config.json'.")
        raise e
    
    # Création des items de la liste déroulante permettant à l'utilisateur de choisir quel algorithme appliquer sur son maillage
    items = [("DEFAULT", "--Choix de l'algorithme--", "")]

    for data in metadata.values():
        # Récupération du nom de la bibliothèque courante
        library_name = data.get("id_name", "")
        # Récupération de la liste des algorithmes associés à la bibliothèque courante
        algorithms = data.get("algorithms", None)
        if algorithms is None:
            raise RuntimeError(f"La bibliothèque {library_name} ne possède pas de champ 'algorithms'.")
        else:
            for algorithm in algorithms:
                # Récupération du nombre de l'algorithme courant
                algorithm_name = algorithm["id_name"]
                # Récupération de la description de l'algorithme
                description = algorithm.get("description", "")
                # création du choix dans a liste déroulante de l'API
                items.append((algorithm_name.upper(), algorithm["name"], description))
                # Stockage de la description de l'algorithme pour l'API dans la table algorithm_description de la structure Globals
                Globals.algorithm_description[algorithm_name] = create_description(description)
                # récupération de la liste des opérations à effectuer avant d'envoyer les données côté C++
                Globals.algorithm_input_pipeline[algorithm_name] = algorithm.get("input", [])
                # Récupération du dictionnaire des propriétés de l'algorithme courant
                properties = algorithm.get("properties", None)
                if properties is not None:
                    # Création d'une liste vide qui contiendra le nom des propriétés de l'algorithme courant
                    properties_name = []
                    # Récupération des données des propriétés de l'algorithme
                    properties_data = properties["data"]
                    # Création d'une classe de propriétés vide héritant de PropertyGroup qui englobera l'ensemble des propriétés de l'algorithme courant
                    property_class = type(properties["class_name"], (bpy.types.PropertyGroup,), {})

                    # Enregistrement de la classe dans le registre de Blender
                    bpy.utils.register_class(property_class)
                    # Ajout des différentes propriétés à la classe
                    for property in properties_data:
                        # Création de la propriété
                        setattr(property_class, property["id_name"], Globals.properties_factory[property["type"]](property["data"]))
                        # Globals.properties_factory[property["type"]](property_class, property["data"], property["id_name"])
                        # ajout du nom de la propriété dans la liste des propriétés de cet algorithme
                        properties_name.append(property["id_name"])
                    # Création d'une nouvelle entrée dans la table "algorithm_properties_name" contenant le nom des propriétés de l'algorithme
                    Globals.algorithm_properties_name[algorithm_name] = tuple(properties_name)
                    # Stockage de la classe nouvellement créée dans une table permettant de la désinscrire du registre de Blender lors de l'appel de la fonction "unregister"
                    Globals.properties_table[algorithm_name] = property_class
                
                    # et référencement de la classe par un attribut
                    setattr(bpy.types.Scene, algorithm_name, bpy.props.PointerProperty(type=property_class))
    
    # Création de la classe de propriétés de l'API Blender qui contiendra la la liste déroulante des algorithmes implémentés
    # ainsi qu"une propriété contenant l'ensemble des messages pouvant être retournés par l'API interne (côté C++)
    # Création de la classe vide
    api_class = type("ApiProperties", (bpy.types.PropertyGroup,), {})
    # Enregistrement de la classe dans le registre de Blender
    bpy.utils.register_class(api_class)
    # Stockage de l'énumération matérialisant la liste déroulante et stockant tous les choix d'algorithme
    setattr(api_class, "algorithm_choice", bpy.props.EnumProperty(name="", items=items, default="DEFAULT"))
    # ainsi que la propriété gérant les messages
    setattr(api_class, "result_infos", bpy.props.StringProperty(
        name="Résultat",
        description="informations sur le ou les résultats de l'algorithme courant utilisé",
        default=""))
    # Stockage de la classe nouvellement créée dans une table permettant de la désinscrire du registre de Blender lors de l'appel de la fonction "unregister"
    Globals.properties_table["api_properties"] = api_class
    # Référencement du groupe de propriétés par un objet de Blender (ici la scène)
    bpy.types.Scene.api_properties = bpy.props.PointerProperty(type=api_class)


# Fonction permettant de vérifier si l'utilisateur a choisi une option de sortie pour l'algorithme choisi (seulement si cette option est disponible)
def is_option_selected(context, algorithm_name):
    # Récupération du groupe de propriétés de l'algorithme courant
    property_group = getattr(context.scene, algorithm_name.lower(), None)
    if property_group is not None:
        # Récupération du choix de l'option de l'utilisateur pour l'algorithme courant
        output_option = getattr(property_group, "output_option", None)
        if output_option is not None:
            if output_option == "DEFAULT":
                return False
            else:
                return True
        else:
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
        context.scene.description_is_hidden = not context.scene.description_is_hidden


    def execute(self, context):
        self.switch_visibility(context)  
        return {"FINISHED"}


class VIEW3D_PT_api_cgal_panel(bpy.types.Panel):
    bl_label = "API C++"  # Titre du panneau latéral
    bl_idname = "VIEW3D_PT_api_cgal_panel"
    bl_space_type = "VIEW_3D"  # espace dans lequel est situé le panneau
    bl_region_type = "UI"  # région dans laquelle le panneau se situe

    bl_category = "API C++"  # nom du panneau dans la barre latérale

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Choisissez un algorithme à appliquer sur le maillage courant :")
        row = layout.row()
        # Récupération du groupe de propriétés de l'API
        api_properties = context.scene.api_properties
        row.scale_y = 1.4
        row.prop(api_properties, "algorithm_choice")
        
        # affichage des propriétés en fonction de l'algorithme choisi par l'utilisateur
        # Récupération du nom de l'algorithme courant
        algorithm_name = api_properties.algorithm_choice
        # Globals.algorithm_properties[current_choice.algorithm_choice]["drawing_properties"](layout, context)
        draw_properties(layout, context, algorithm_name)
        # création d'une nouvelle ligne dans laquelle nous ajoutons un bouton (instance de la classe VIEW3D_OT_api_cgal)
        if algorithm_name != "DEFAULT":
             # Récupération de la description de l'algorithme
            description = Globals.algorithm_description[algorithm_name.lower()]
            row = layout.row()
            row.label(text="Description de l'algorithme :", icon="QUESTION")
            box = layout.box()
            # Récupération du booléen gérant l'affichage ou le masquage partiel de la description de l'algorithme
            description_is_hidden = context.scene.description_is_hidden
            label = "Etendre la description" if description_is_hidden else "Réduire la description"
            if description_is_hidden:
                box.label(text=description[0][:-3] + "...")
            else:
                for line in description:
                    box.label(text=line)
            row = box.row()
            row.scale_y = 1.2
            row.operator(VIEW3D_OT_display_description.bl_idname, text=label)
            row = layout.row()
            row.enabled = is_option_selected(context, algorithm_name)
            row.scale_y = 1.7
            # l'opérateur est référencé par un nom correspondant à la valeur de l'attribut bl_idname de la classe
            row.operator(VIEW3D_OT_execute_algorithm.bl_idname, text="Appliquer l'algorithme")
        else:
            pass

        if api_properties.result_infos != "":
            for line in api_properties.result_infos.splitlines():
                layout.label(text=line)
        else:
            pass


## Fonctions d'enregistrement, de désincription et de référencement des groupe de propriétés des classes de l'API
classes = (VIEW3D_PT_api_cgal_panel, VIEW3D_OT_display_description, VIEW3D_OT_execute_algorithm)

def algorithm_properties_registering():
    # ainsi que toutes les classes de propriétés des algorithmes de l'API
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
    # Enregistrement des classes basiques (panneau, boutons, ...) dans le registre de Blender
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.description_is_hidden = bpy.props.BoolProperty(name="Afficher/Masquer la description de l'algorithme", default=True)
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
    del bpy.types.Scene.description_is_hidden
    # Suppression des pointeurs référençant les propriétés des algorithmes de l'API
    delete_property_pointers()


if __name__ == "__main__":
    register()
