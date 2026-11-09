import os, sys, random
os.environ["SDL_VIDEODRIVER"]="dummy"
proj=sys.argv[1]; sys.path.insert(0,proj)
import pygame, aplikacja as ap, algorytmy as alg
pygame.init(); screen=pygame.display.set_mode((ap.WIDTH,ap.HEIGHT))
random.seed(7)
app=ap.App(screen)
out=os.path.join(proj,"dokumentacja","obrazy")
app.draw(); pygame.image.save(screen, os.path.join(out,"gui_start.png"))
app._iterate(3); app.message="Iteracja 3 - feromon jest jeszcze rozproszony."; app.draw(); pygame.image.save(screen, os.path.join(out,"gui_iter3.png"))
app._iterate(97); app.message="Iteracja 100 - kolonia skupiła się na krótkiej trasie."; app.draw(); pygame.image.save(screen, os.path.join(out,"gui_iter100.png"))
# blokada
e=sorted(alg.tour_edges(app.colony.best_tour))[3]
app.block_mode=True; app.toggle_block(e)
for _ in range(200):
    app._iterate(1)
    if app.block_event["found"] is not None: break
print("block found", app.block_event)
app._iterate(30); app.draw(); pygame.image.save(screen, os.path.join(out,"gui_blokada.png"))
app.block_mode=False
app.run_compare(); app.overlay="2-opt"; app.draw(); pygame.image.save(screen, os.path.join(out,"gui_porownanie.png"))
print({k:(v[1],v[2]) if isinstance(v,tuple) else v for k,v in app.compare.items()})
# zdarzenia myszy: dodawanie, usuwanie, przeciąganie
n=len(app.points)
app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=(100,100),button=1)); assert len(app.points)==n+1
app.handle(pygame.event.Event(pygame.MOUSEBUTTONUP,pos=(100,100),button=1))
app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=(100,100),button=3)); assert len(app.points)==n
for b in app.buttons: b.action()
app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=(ap.PANEL_X+200, app.s_alpha.track.centery),button=1)); print("alpha",app.s_alpha.value)
app.clear(); app.draw(); app.run_compare(); app.toggle_run(); print("ok", app.message)
