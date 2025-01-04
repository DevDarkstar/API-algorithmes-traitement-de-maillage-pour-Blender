import bpy
import os
import sys
import subprocess
import platform

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
