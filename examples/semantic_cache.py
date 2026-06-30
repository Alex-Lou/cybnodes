"""Cache SEMANTIQUE calibre : repondre instantanement a une question deja vue (ou proche),
sans rejouer reseaux/web/modele -- en CALIBRANT le seuil sur tes donnees pour ne JAMAIS servir
une reponse proche-mais-fausse (la sincerite avant la vitesse).

La methode validee (la "courbe") : on rassemble des paires etiquetees -- celles qui DOIVENT
partager une reponse (positifs) et celles qui ne doivent PAS (negatifs, dont les "faux amis"
tres proches mais a reponse differente) -- on balaie le seuil, et on prend le plus bas qui tient
un faux-hit-rate cible. CybNodes ne depend de rien : tu INJECTES l'embedder (ici une demo aux
cosinus realistes ; en prod sentence-transformers / OpenAI / Ollama).

    python examples/semantic_cache.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybnodes import Result, SemanticCache

# Embedder DEMO : quelques phrases reelles -> vecteurs aux cosinus realistes (ce qu'un VRAI
# modele produirait). 'chien' est un FAUX AMI : tres proche de 'chat' (0.92) mais autre reponse.
_DEMO = {
    "c est quoi un chat":  [1.00, 0.000],   # reference
    "parle moi des chats": [0.98, 0.199],   # ~0.98 de 'chat' (MEME reponse : paraphrase)
    "c est quoi un chien": [0.92, 0.392],   # ~0.92 de 'chat' (FAUX AMI : autre reponse)
    "quel temps fait il":  [0.00, 1.000],   # autre sujet
    "il pleut dehors":     [0.05, 0.999],   # autre sujet
}


def embed(text):
    k = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (text or "").lower())).strip()
    return _DEMO.get(k, [0.0, 0.0])


cache = SemanticCache(embedder=embed)

# 1) CALIBRER sur tes paires etiquetees -> la "courbe" + le seuil choisi
positifs = [("c'est quoi un chat", "parle-moi des chats")]                       # ~0.98 (meme reponse)
negatifs = [("c'est quoi un chat", "c'est quoi un chien"),                       # ~0.92 (FAUX AMI)
            ("c'est quoi un chat", "quel temps fait-il")]                        # ~0.00
seuil, courbe = cache.calibrate(positifs, negatifs, target_false_hit_rate=0.0)
print("seuil calibre (cible faux-hit 0%%) : %.2f  -> il passe AU-DESSUS du faux ami (0.92)" % seuil)

# 2) UTILISER le cache : on stocke une reponse SURE, et on regarde qui y a droit
cache.put("c'est quoi un chat ?", Result(kind="savoir", text="Le chat est un petit felin.", confidence=0.9))

print("\nrequetes (apres calibration) :")
for q in ["c'est quoi un chat ?",       # EXACT          -> hit
          "parle-moi des chats",        # paraphrase 0.98 -> hit
          "c'est quoi un chien ?",      # FAUX AMI 0.92   -> MISS (on ne ment pas !)
          "quel temps fait-il ?"]:      # autre sujet     -> MISS
    hit = cache.get(q)
    print("   %-26s %s" % (q, hit.text if hit else "[MISS -> on recalcule, on n'invente pas]"))
print("\nstats :", cache.stats())
