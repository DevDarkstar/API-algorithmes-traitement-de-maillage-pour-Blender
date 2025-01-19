import pymeshlab
import numpy as np

class PyMeshApi:
    """Classe permettant de communiquer entre l'extension Blender et le module pymeshlab"""

    def __init__(self, data):
        self.data = data
        self.result = {}

    def init(self):
        """Exécution de l'algorithme MeshLab choisi par l'utilisateur"""
        # Vérification de la présence des informations nécessaires à l'exécution d'un algorithme de MashLab dans l'attribut data
        # Récupération des coordonnées des sommets du maillage contenues dans un tableau numpy
        vertices = self.data.get("vertices", None)
        if vertices is not None:
            # Remise en forme des données du tableau de sorte à transformer le tableau initial à 1 dimension en un tableau à 
            # 2 dimensions (nombre de sommmets pour la première dimension et les 3 coordonnées spatiales pour la seconde)
            vertices = np.reshape(vertices, (vertices.shape[0] // 3, 3))
        else:
            raise RuntimeError("Le dictionnaire des données ne possède pas les coordonnées des sommets.")

        # Pareil pour les indices des sommets des faces
        faces = self.data.get("faces", None)
        if faces is not None:
            faces = np.reshape(faces, (faces.shape[0] // 3, 3))
        else:
            raise RuntimeError("Le dictionnaire des données ne possède pas les indices des sommets des faces.")
        
        # Récupération du nom de la fonction MeshLab utilisée pour exécuter l'algorithme
        functions_name = self.data.get("function", None)
        if functions_name is None:
            raise RuntimeError("Le dictionnaire des données ne possède pas le nom de la fonction MeshLab à exécuter.")
        
        # Récupération des éventuels paramètres utilisés pour la fonction MeshLab
        params = self.data.get("params")

        # Création d'un MeshSet pour exécuter l'algorithme
        ms = pymeshlab.MeshSet()

        # Création d'un maillage à partir des coordonnées des sommets et des indices des sommets des faces
        mesh = pymeshlab.Mesh(vertex_matrix=vertices, face_matrix=faces)

        # Ajout du maillage dans le MeshSet
        ms.add_mesh(mesh)

        # Exécution des sous-algorithmes de l'algorithme principal sur le maillage sous la forme d'un application de filtre
        for function_name, param in zip(functions_name, params):
            ms.apply_filter(function_name, **param)

        # Récupération du maillage résultant
        resulting_mesh = ms.current_mesh()

        # Récupération des données en fonction de la fonction MeshLab utilisée
        if all(function_name in ["compute_curvature_and_color_apss_per_vertex"] for function_name in functions_name):
            self.result["output_result"] = ["vertex_coloration"]
            self.result["colors"] = resulting_mesh.vertex_color_matrix().flatten()
        elif all(function_name in ["meshing_isotropic_explicit_remeshing", "create_fractal_terrain"] for function_name in functions_name):
            self.result["output_result"] = ["replace_mesh"]
            self.result["vertices"] = resulting_mesh.vertex_matrix().flatten()
            self.result["faces"] = resulting_mesh.face_matrix().flatten()
        else:
            raise RuntimeError("La fonction MeshLab demandée n'est pas encore implantée dans l'extension.")

           
    def get_result(self):
        return self.result
