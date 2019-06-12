import pygame
import numpy as np
from numpy import sin, cos, pi
import random
import sys

BLACK, GRAY, WHITE, RED = (0,0,0), (50,50,50), (255,255,255), (255,100,100)
FPS = 60

class SpiralsHandler(object):

    def __init__(self, view_size, n_vertices_base_shapes, max_active_spirals=3):
        self.view_size = np.array(view_size)
        self.max_active_spirals = max_active_spirals

        self.poly_vertices = [[rotate([0,-1],i*2*pi/n) for i in range(n)] for n in n_vertices_base_shapes]
        self.etas          = [0.15, 0.1, 0.05]
        self.growth_rates  = [0.0007, 0.0008, 0.0009, 0.0010]
        self.chiralities   = ['+', '-']

        self.spirals = []

        self.add_random_spiral()


    def take_n_steps(self, n, dT=int(1000/FPS)):
        for spiral in self.spirals:
            for i in range(n):
                spiral.step(dT)


    def random_spiral_transition(self):
        if len(self.spirals) > 0:
            self.disable_random_spiral()
            self.add_random_spiral()


    def add_random_spiral(self):
        if sum([s.active for s in self.spirals]) < self.max_active_spirals:
            poly_vertices = random.choice(self.poly_vertices)
            eta           = random.choice(self.etas)
            growth_rate   = random.choice(self.growth_rates)
            chirality     = random.choice(self.chiralities)

            self.spirals.append(Spiral(poly_vertices, chirality, self.view_size, self.view_size/2, eta, growth_rate))


    def disable_random_spiral(self):
        active_spirals = [s for s in self.spirals if s.active]
        if len(active_spirals) > 0:
            s = random.choice(active_spirals)
            s.active = False


    def step(self, dT):
        for spiral in self.spirals: spiral.step(dT)

        # remove spirals that don't have any lines anymore:
        self.spirals = [spiral for spiral in self.spirals if len(spiral.lines)>0]


    def get_all_lines(self):
        return [line for spiral in self.spirals for line in spiral.lines]


class Spiral(object):
    MAX_LINES = 10000
    MIN_LENGHT = 10
    MAX_SPIRAL_CENTER_DEVIATION = 10

    def __init__(self, poly_vertices, chirality, view_size, center, eta=0.1, growth_rate=0.001):
        self.chirality     = chirality
        self.view_size     = np.array(view_size)
        self.center        = np.array(center)
        self.eta           = eta
        self.growth_rate   = growth_rate

        assert chirality in ['+','-']
        assert eta > 0 and eta < 1
        assert growth_rate > 0

        self.active = True
        self.n_vert = len(poly_vertices)
        self.lines  = []

        if chirality == '-':
            poly_vertices = poly_vertices[::-1]

        for i in range(len(poly_vertices)):
            p1 = np.array(poly_vertices[i-1]) + self.center
            p2 = np.array(poly_vertices[i]) + self.center
            self.lines.append(np.array([p1,p2]))


    def __str__(self):
        return 'Spiral: [{}{}] eta: {} growth_rate: {} n_lines: {} active: {}'.format(self.n_vert, self.chirality, self.eta, self.growth_rate, len(self.lines), self.active)


    def _is_line_visible(self, line):
        # TODO: this functions is now too conservative. Check intersection between 
        # view-box edges and line

        if (line[0][0] > 0 and line[0][0] < self.view_size[0] or
            line[0][1] > 0 and line[0][1] < self.view_size[1] or 
            line[1][0] > 0 and line[1][0] < self.view_size[0] or
            line[1][1] > 0 and line[1][1] < self.view_size[1]): return True

        return False


    def _spiral_center(self):
        """the center of the spiral is defined as the geometric average of the last 'n_vert' lines"""

        if len(self.lines) > 0: return average_point_of_lines(self.lines[-self.n_vert:])
        else:                   return self.center


    def step(self, dT):
        spiral_center = self._spiral_center()

        # When the final lines of a spiral are about to get deleted, the center 
        # of the spiral might jump around leading to graphical glitches. If the 
        # center deviates too much from the actual center of the screen, remove 
        # the spiral.
        if np.linalg.norm(spiral_center-self.center) > self.MAX_SPIRAL_CENTER_DEVIATION:
            self.lines = []
            return

        s = 1. + self.growth_rate * dT

        self.lines = [s*(line-spiral_center) + self.center for line in self.lines]

        # Now add lines in the spiral until the newly added line is smaller than a thrshold:
        if self.active:
            while np.linalg.norm(self.lines[-1][0] - self.lines[-1][1]) > self.MIN_LENGHT:
                for i in range(self.n_vert):
                    i,j = len(self.lines)-1, len(self.lines)-self.n_vert+1
                    self.lines.append(np.array([self.lines[i][1], eta_point(self.lines[j],self.eta)]))
                if len(self.lines) > self.MAX_LINES: sys.exit("Too many lines in spiral")

        # Remove lines that are no longer visible:
        self.lines = [line for line in self.lines if self._is_line_visible(line)]


def eta_point(line, eta):
    return line[0] + eta*(line[1]-line[0])


def average_point_of_lines(lines):
    centers = [eta_point(line,0.5) for line in lines]
    x_c = np.average([p[0] for p in centers])
    y_c = np.average([p[1] for p in centers])
    return np.array([x_c,y_c])


def rotate(p, theta):
    assert len(p)==2
    return [p[0]*cos(theta)-p[1]*sin(theta), p[0]*sin(theta)+p[1]*cos(theta)]


class App(object):

    def __init__(self, size=(640,640)):
        pygame.init()
        self._running = True
        self.size = size

        self.spirals_handler = SpiralsHandler(self.size, [3,4,5,6])

        self.display_surf = pygame.display.set_mode(self.size, pygame.HWSURFACE | pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()
        self.show_help = True
        self.time_prefactor = 1.


    def handle_events(self, event):
        if event.type == pygame.QUIT:
            self._running = False

        elif event.type == pygame.KEYDOWN:
            if   event.key == pygame.K_ESCAPE: self._running = False
            elif event.key == pygame.K_h:      self.show_help = not self.show_help
            elif event.key == pygame.K_t:      self.spirals_handler.random_spiral_transition()
            elif event.key == pygame.K_a:      self.spirals_handler.add_random_spiral()
            elif event.key == pygame.K_r:      self.spirals_handler.disable_random_spiral()
            elif event.key == pygame.K_s:      self.spirals_handler.take_n_steps(1000)
            elif event.key == pygame.K_UP:     self.time_prefactor *= 1.2
            elif event.key == pygame.K_DOWN:   self.time_prefactor *= 1/1.2


    def loop_logic(self):
        dT = self.time_prefactor * self.clock.tick(FPS)
        self.spirals_handler.step(dT)


    def render(self):
        surface = pygame.Surface(self.size)
        surface.fill(GRAY)

        for line in self.spirals_handler.get_all_lines():
            pygame.draw.aaline(surface,WHITE,line[0],line[1])
            # pygame.draw.line(surface,GRAY,line[0],line[1], 2)

        self.display_surf.blit(surface, (0,0))

        if self.show_help:
            self.help_text()

        pygame.display.flip()


    def help_text(self):
        y_size = 12
        y = y_size
        myfont = pygame.font.SysFont("Courier", y_size)

        def add_help_label(text):
            nonlocal y
            label = myfont.render(text, 1, RED)
            self.display_surf.blit(label, (10, y))
            y += y_size

        add_help_label("Controls")
        add_help_label("========")
        add_help_label("h    : hide/show help")
        add_help_label("t    : random transition")
        add_help_label("a    : add random spiral")
        add_help_label("r    : remove random spiral")
        add_help_label("s    : skip 100 frames")
        add_help_label("up   : speed up")
        add_help_label("down : speed down")
        add_help_label("esc  : quit")
        add_help_label("")
        add_help_label("Info")
        add_help_label("====")
        add_help_label("FPS: {0:.2f}".format(self.clock.get_fps()))
        add_help_label("Delta T prefactor: {0:.2f}".format(self.time_prefactor))
        add_help_label("Total # lines: {}".format(len(self.spirals_handler.get_all_lines())))
        for i,spiral in enumerate(self.spirals_handler.spirals):
            add_help_label(str(spiral))


    def cleanup(self):
        pygame.quit()
 

    def run(self):
        while(self._running):
            for event in pygame.event.get():
                self.handle_events(event)

            self.loop_logic()
            self.render()

        self.cleanup()
 

if __name__ == "__main__" :
    app = App()
    app.run()





