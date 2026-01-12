from OpenGL.GL import *
from OpenGL.GLUT import *  # Import all GLUT functions
from OpenGL.GLU import *
import math
import random
import sys
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
from OpenGL.GLUT import GLUT_BITMAP_TIMES_ROMAN_24


# Camera-related variables
camera_pos = (0, 500, 500)
fovY = 120
GRID_LENGTH = 1500
MARGIN = 50  # buffer so objects stay inside walls

camera_mode = "third"   # "third" or "first"
# Rotor animation variable
rotor_angle = 0
# Movement variables for friendly helicopter
heli_time_friend = 1.5   # offset so they don't overlap
# Searchlight rotation angle
search_angle = 0.0
player_ammo = 50

game_over = False

########################################################################
# --- Gameplay state ---
score = 0
win = False
paused = False

# --- Timer (real time) ---
import time
TIMER_LIMIT_SECONDS = 120  # 2 minutes
timer_start = None  # set when game starts or restarts

# --- UI buttons (screen-space rectangles) ---
# Coordinates in orthographic HUD space (0..1000 x 0..800)
UI_PAUSE_BTN = {"x": 860, "y": 740, "w": 100, "h": 40}   # shows "Pause" or "Play"
UI_EXIT_BTN  = {"x": 970, "y": 740, "w": 40,  "h": 40}  # shows "X"

# --- Diamonds (collectibles) ---
diamonds = []  # each diamond: [x, y, z, is_air, base_size, phase]
MAX_DIAMONDS = 10
DIAMOND_SPAWN_MIN = 5
DIAMOND_SPAWN_MAX = 10

# --- Friendly helicopter (one) ---
friendly_heli = {
    "pos": [0, 0, 220],
    "target": [200, -150, 220],
    "alive": True
}

# --- Gun pitch control ---
gun_pitch = 0.0  # up/down angle in degrees, affects bullet direction

# --- Crate spawn control tied to friendly heli ---
friendly_crate_timer = 0  # only drops crates if friendly heli is alive
FRIENDLY_CRATE_INTERVAL = 180  # frames between drops (adjust as needed)
########################################################################


#HUD
hud_flash = 0



# Player and detection variables
player_pos = [0.0, 0.0, 0.0]  # x, y, z on ground
player_yaw = 0.0  # ✅ FIX 2: Added player yaw for rotation
player_speed = 15

# Player stats (Member 2)
player_health = 100
player_ammo = 100
player_armour = 25
player_mode = "ground"
switch_anim = 0
is_switching = False
move_speed_ground = 12
move_speed_air = 18
player_bullets = []
ground_cooldown = 0
air_cooldown = 0
hit_flash = 0
heal_glow = 0

# Gun animation
gun_angle = 0.0


# ✅ Step 2: Initialize non-overlapping obstacles
obstacles = []
NUM_OBSTACLES = 10

def overlaps(x, y, w, h, obstacles):
    for ox, oy, ow, oh in obstacles:
        if (abs(x - ox) < (w/2 + ow/2)) and (abs(y - oy) < (h/2 + oh/2)):
            return True
    return False

for i in range(NUM_OBSTACLES):
    while True:
        ox = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        oy = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)

        w = random.randint(80, 200)
        h = random.randint(80, 200)

        if not overlaps(ox, oy, w, h, obstacles):
            obstacles.append([ox, oy, w, h])
            break

trees = []   # each tree = [x, y]
NUM_TREES = 20  # increase density
def tree_overlaps_obstacle(tx, ty, obstacles):
    for ox, oy, w, h in obstacles:
        if (ox - w/2 < tx < ox + w/2) and (oy - h/2 < ty < oy + h/2):
            return True
    return False

for i in range(NUM_TREES):
    while True:
        tx = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        ty = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        if not tree_overlaps_obstacle(tx, ty, obstacles):
            trees.append([tx, ty])
            break





# ✅ FIX 1: Removed global destruction_timer (now per-helicopter)

# Enemy bullets
enemy_bullets = []
enemy_tank_bullets = []
enemy_fire_timer = 0

# Crates
crates = []   # each crate = [x, y, z, type]
crate_drop_timer = 0
MAX_CRATES = 8  # Limit maximum crates

# FIX 1: Anti-collision parameters
SAFE_HELI_DISTANCE = 120

# FIX 3: Multiple enemy helicopters
NUM_ENEMY_HELIS = 4
enemy_helis = []
# ================= ENEMY TANKS =================
NUM_ENEMY_TANKS = 5
enemy_tanks = []

for i in range(NUM_ENEMY_TANKS):
    enemy_tanks.append({
        "pos": [
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            0
        ],
        "yaw": 0.0,
        "fire_timer": random.randint(0, 80),
        "health": 60,
        "alive": True
    })

# Initialize enemy helicopters with destruction state
for i in range(NUM_ENEMY_HELIS):
    enemy_helis.append({
        "pos": [random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
                random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
                random.randint(180, 260)],
        "target": [random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
                   random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
                   random.randint(180, 260)],
        "fire_timer": random.randint(0, 25),
        "detected": False,
        "yaw": 0.0,
        "destroy_timer": 0,
        "alive": True
    })




def collides(nx, ny):
    # Boundary check
    if nx < -GRID_LENGTH + MARGIN or nx > GRID_LENGTH - MARGIN:
        return True
    if ny < -GRID_LENGTH + MARGIN or ny > GRID_LENGTH - MARGIN:
        return True

    # Trees
    for tx, ty in trees:
        if math.sqrt((nx - tx)**2 + (ny - ty)**2) < 40:
            return True

    # Obstacles
    for ox, oy, w, h in obstacles:
        if (ox - w/2 < nx < ox + w/2) and (oy - h/2 < ny < oy + h/2):
            return True

    return False

def safe_spawn():
    while True:
        x = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        y = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        if not collides(x, y):   # ✅ only accept safe positions
            return [x, y, 0]

player_pos = player_pos = [0.0, 0.0, 0.0]

def start_timer():
    global timer_start
    timer_start = time.time()

def get_elapsed_seconds():
    if timer_start is None:
        return 0
    return int(time.time() - timer_start)

def reset_game():
    global score, win, game_over, paused
    global player_health, player_ammo, player_armour
    global player_pos, player_yaw, player_mode, switch_anim, is_switching
    global player_bullets, enemy_bullets, crates, diamonds
    global gun_angle, gun_pitch
    global enemy_helis, friendly_heli
    global hud_flash, hit_flash, heal_glow
    global friendly_crate_timer

    # Core state
    score = 0
    win = False
    game_over = False
    paused = False

    # Player reset
    player_health = 100
    player_ammo = 100
    player_armour = 25
    player_pos = [0.0, 0.0, 0.0]
    player_yaw = 0.0
    player_mode = "ground"
    switch_anim = 0
    is_switching = False
    player_bullets.clear()
    enemy_bullets.clear()
    gun_angle = 0.0
    gun_pitch = 0.0

    # Effects
    hud_flash = 0
    hit_flash = 0
    heal_glow = 0

    # Collectibles and crates
    crates.clear()
    diamonds.clear()
    friendly_crate_timer = 0

    # Enemy helis: keep 4 alive
    for heli in enemy_helis:
        heli["alive"] = True
        heli["destroy_timer"] = 0
        heli["detected"] = False
        heli["pos"] = [
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            random.randint(180, 260)
        ]
        heli["target"] = [
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            random.randint(180, 260)
        ]
        heli["fire_timer"] = random.randint(0, 25)

    # Friendly heli returns on reset
    friendly_heli["alive"] = True
    friendly_heli["pos"] = [0, 0, 220]
    friendly_heli["target"] = [200, -150, 220]

    start_timer()



#diamonds
def spawn_diamonds():
    global diamonds
    if len(diamonds) >= MAX_DIAMONDS:
        return
    count = random.randint(DIAMOND_SPAWN_MIN, DIAMOND_SPAWN_MAX)
    for _ in range(count):
        x = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        y = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        is_air = random.random() < 0.5  # half in air, half on ground
        z = random.randint(120, 220) if is_air else 0
        base_size = random.randint(12, 22)
        phase = random.random() * 2 * math.pi
        diamonds.append([x, y, z, is_air, base_size, phase])

def update_and_draw_diamonds():
    global diamonds, score, hud_flash
    to_remove = []

    for d in diamonds:
        x, y, z, is_air, base_size, phase = d
        # Pulsation
        phase += 0.15
        size = base_size + 6 * math.sin(phase)
        d[5] = phase

        # Draw diamond (octahedron-like)
        glPushMatrix()
        glTranslatef(x, y, z)
        glColor3f(0.2, 0.9, 1.0)  # cyan-ish
        glBegin(GL_TRIANGLES)
        # top pyramid
        glVertex3f(0, 0, size)
        glVertex3f(-size/2, 0, 0)
        glVertex3f(0, -size/2, 0)

        glVertex3f(0, 0, size)
        glVertex3f(0, -size/2, 0)
        glVertex3f(size/2, 0, 0)

        glVertex3f(0, 0, size)
        glVertex3f(size/2, 0, 0)
        glVertex3f(0, size/2, 0)

        glVertex3f(0, 0, size)
        glVertex3f(0, size/2, 0)
        glVertex3f(-size/2, 0, 0)

        # bottom pyramid
        glVertex3f(0, 0, -size)
        glVertex3f(0, -size/2, 0)
        glVertex3f(-size/2, 0, 0)

        glVertex3f(0, 0, -size)
        glVertex3f(size/2, 0, 0)
        glVertex3f(0, -size/2, 0)

        glVertex3f(0, 0, -size)
        glVertex3f(0, size/2, 0)
        glVertex3f(size/2, 0, 0)

        glVertex3f(0, 0, -size)
        glVertex3f(-size/2, 0, 0)
        glVertex3f(0, size/2, 0)
        glEnd()
        glPopMatrix()

        # Collection check
        dx = x - player_pos[0]
        dy = y - player_pos[1]
        dz = z - player_pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Ground diamonds: require player near on ground; Air diamonds: require near in air
        if is_air:
            if player_mode == "air" and dist < 40:
                score += 5
                hud_flash = 8
                to_remove.append(d)
        else:
            if player_mode == "ground" and math.sqrt(dx*dx + dy*dy) < 40 and abs(player_pos[2] - 0) < 10:
                score += 5
                hud_flash = 8
                to_remove.append(d)

    for d in to_remove:
        diamonds.remove(d)

    # Keep diamond population up
    if len(diamonds) < DIAMOND_SPAWN_MIN:
        spawn_diamonds()




def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


    if camera_mode == "third":
        # Camera offset behind and above player
        cam_distance = 220
        cam_height = 160

        rad = math.radians(player_yaw)

        cam_x = player_pos[0] - math.cos(rad) * cam_distance
        cam_y = player_pos[1] - math.sin(rad) * cam_distance
        cam_z = player_pos[2] + cam_height

        gluLookAt(
            cam_x, cam_y, cam_z,
            player_pos[0], player_pos[1], player_pos[2] + 40,
            0, 0, 1
        )



    else:  # FIRST PERSON (FIXED)
        px, py, pz = player_pos
        rad = math.radians(player_yaw)

        # Camera at vehicle front
        eye_x = px + math.cos(rad) * 30
        eye_y = py + math.sin(rad) * 30
        eye_z = pz + 40

        # Look forward
        center_x = eye_x + math.cos(rad) * 200
        center_y = eye_y + math.sin(rad) * 200
        center_z = eye_z

        gluLookAt(
            eye_x, eye_y, eye_z,
            center_x, center_y, center_z,
            0, 0, 1
        )


def draw_obstacle(x, y, w, h):
    glColor3f(0.3, 0.3, 0.3)  # gray block
    glPushMatrix()
    glTranslatef(x, y, 15)    # lift above ground
    glScalef(w-50, h, 10)        # thickness
    glutSolidCube(1)
    glPopMatrix()


def show_game_over():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(1, 0, 0)  # red text
    glRasterPos2f(400, 400)
    for c in "GAME OVER":
        glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))

    glRasterPos2f(350, 350)
    for c in "Press ESC to Exit":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    glutSwapBuffers()

def show_win():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(0, 1, 0)  # green text
    glRasterPos2f(420, 420)
    for c in "YOU WIN":
        glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))

    glRasterPos2f(350, 360)
    for c in "Press ESC to Exit or R to Restart":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    glutSwapBuffers()




def draw_tree(x, y):
    # Trunk
    glColor3f(0.55, 0.27, 0.07)  # brown
    glPushMatrix()
    glTranslatef(x, y, 25)
    glScalef(10, 10, 50)
    glutSolidCube(1)
    glPopMatrix()

    # Foliage
    glColor3f(0.0, 0.6, 0.0)     # green
    glPushMatrix()
    glTranslatef(x, y, 70)
    glutSolidSphere(25, 16, 16)  # round leafy top
    glPopMatrix()



def draw_grid_floor(size, step=40):
    for x in range(-size, size, step):
        for y in range(-size, size, step):
            if (x//step + y//step) % 2 == 0:
                glColor3f(0.75, 0.75, 0.75)  # light tile
            else:
                glColor3f(0.55, 0.55, 0.55)  # dark tile

            glBegin(GL_QUADS)
            glVertex3f(x, y, 0)
            glVertex3f(x+step, y, 0)
            glVertex3f(x+step, y+step, 0)
            glVertex3f(x, y+step, 0)
            glEnd()
def draw_arena_walls(size=600, height=120):
    thickness = 20

    # North wall (blue)
    glColor3f(0.2, 0.4, 0.8)
    glPushMatrix()
    glTranslatef(0, size, height/2)
    glScalef(size*2, thickness, height)
    glutSolidCube(1)
    glPopMatrix()

    # South wall (cyan)
    glColor3f(0.2, 0.8, 0.8)
    glPushMatrix()
    glTranslatef(0, -size, height/2)
    glScalef(size*2, thickness, height)
    glutSolidCube(1)
    glPopMatrix()

    # East wall (green)
    glColor3f(0.2, 0.8, 0.4)
    glPushMatrix()
    glTranslatef(size, 0, height/2)
    glScalef(thickness, size*2, height)
    glutSolidCube(1)
    glPopMatrix()

    # West wall (teal)
    glColor3f(0.0, 0.6, 0.6)
    glPushMatrix()
    glTranslatef(-size, 0, height/2)
    glScalef(thickness, size*2, height)
    glutSolidCube(1)
    glPopMatrix()

#shadow under helicopter

def draw_shadow(x, y):
    glColor4f(0, 0, 0, 0.25)
    glPushMatrix()
    glTranslatef(x, y, 0.1)
    glutSolidSphere(30, 20, 20)
    glPopMatrix()



def draw_player_vehicle():
    global switch_anim, gun_angle, hit_flash, heal_glow

    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2] + 25)
    glScalef(0.8, 0.8, 0.8)

    # ✅ FIX 2: Apply player rotation
    glRotatef(player_yaw, 0, 0, 1)

    # ---------- Smooth transform effect ----------
    # ground -> air: slightly taller + sleeker
    t = switch_anim  # 0..1 during switching
    if player_mode == "ground":
        glScalef(1.0, 1.0, 1.0 - 0.25 * t)
    else:
        glScalef(1.0, 1.0, 1.0 + 0.25 * t)

    # =========================================================
    # 1) MAIN ARMORED HULL (layered body)
    # =========================================================
    glPushMatrix()
    glColor3f(0.10, 0.25, 0.60)  # armored blue
    glScalef(2.2, 1.4, 0.7)
    glutSolidCube(40)
    glPopMatrix()

    # Top armor plate
    glPushMatrix()
    glColor3f(0.12, 0.30, 0.70)
    glTranslatef(0, 0, 18)
    glScalef(1.8, 1.1, 0.25)
    glutSolidCube(40)
    glPopMatrix()

    # Front wedge armor
    glPushMatrix()
    glColor3f(0.08, 0.22, 0.55)
    glTranslatef(38, 0, 5)
    glRotatef(20, 0, 1, 0)
    glScalef(0.9, 1.0, 0.5)
    glutSolidCube(30)
    glPopMatrix()

    # Side armor skirts
    for side in (-1, 1):
        glPushMatrix()
        glColor3f(0.07, 0.18, 0.45)
        glTranslatef(0, side * 32, -5)
        glScalef(1.8, 0.18, 0.5)
        glutSolidCube(40)
        glPopMatrix()

    # =========================================================
    # 2) TURRET + CANNON (multi-purpose)
    # =========================================================
    # Turret base
    glPushMatrix()
    glTranslatef(5, 0, 25)
    glColor3f(0.15, 0.20, 0.30)
    glScalef(1.0, 0.8, 0.35)
    glutSolidCube(35)
    glPopMatrix()

    # Turret dome
    glPushMatrix()
    glTranslatef(5, 0, 33)
    glColor3f(0.18, 0.22, 0.35)
    glutSolidSphere(12, 14, 14)
    glPopMatrix()

    # Cannon (uses your gun_angle as aiming animation)
    glPushMatrix()
    glTranslatef(25, 0, 28)
    glRotatef(gun_angle, 0, 1, 0)    # recoil/aim animation you already have
    glRotatef(90, 0, 1, 0)           # point along +X
    glColor3f(0.75, 0.75, 0.85)
    gluCylinder(gluNewQuadric(), 4, 4, 35, 12, 12)
    # muzzle tip
    glTranslatef(0, 0, 35)
    glColor3f(0.55, 0.55, 0.65)
    gluCylinder(gluNewQuadric(), 5, 3, 8, 12, 12)
    glPopMatrix()

    # Side mini-guns (visual multipurpose)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(10, side * 18, 18)
        glRotatef(90, 0, 1, 0)
        glColor3f(0.40, 0.40, 0.45)
        gluCylinder(gluNewQuadric(), 2.2, 2.2, 18, 10, 10)
        glPopMatrix()

    # =========================================================
    # 3) GROUND MODE: WHEELS/TRACKS
    # =========================================================
    if player_mode == "ground":
        # 4 wheels (cylinders) + hubs
        wheel_x = [-25, 25]
        wheel_y = [-22, 22]
        for wx in wheel_x:
            for wy in wheel_y:
                glPushMatrix()
                glTranslatef(wx, wy, -18)
                glRotatef(90, 1, 0, 0)  # cylinder axis alignment
                glColor3f(0.08, 0.08, 0.08)
                gluCylinder(gluNewQuadric(), 8, 8, 10, 14, 14)
                # hub cap
                glTranslatef(0, 0, 5)
                glColor3f(0.25, 0.25, 0.25)
                glutSolidSphere(4, 10, 10)
                glPopMatrix()

    # =========================================================
    # 4) AIR MODE: WINGS + THRUSTERS
    # =========================================================
    else:
        # Wings
        for side in (-1, 1):
            glPushMatrix()
            glColor3f(0.35, 0.55, 0.95)
            glTranslatef(0, side * 42, 5)
            glScalef(2.4, 0.12, 0.35)
            glutSolidCube(35)
            glPopMatrix()

        # Rear thrusters (2)
        for side in (-1, 1):
            glPushMatrix()
            glTranslatef(-45, side * 12, 5)
            glRotatef(90, 0, 1, 0)
            glColor3f(0.20, 0.20, 0.25)
            gluCylinder(gluNewQuadric(), 6, 6, 18, 12, 12)
            # glow nozzle
            glTranslatef(0, 0, 18)
            glColor3f(0.20, 0.90, 1.00)
            glutSolidSphere(5, 12, 12)
            glPopMatrix()

        # small stabilizer fin
        glPushMatrix()
        glColor3f(0.25, 0.40, 0.85)
        glTranslatef(-30, 0, 28)
        glScalef(0.8, 0.12, 0.8)
        glutSolidCube(25)
        glPopMatrix()

    # =========================================================
    # 5) Damage / Heal overlays (your existing effects)
    # =========================================================
    if hit_flash > 0:
        glPushMatrix()
        glColor4f(1, 0, 0, hit_flash / 10.0)
        glutSolidSphere(80, 12, 12)
        glPopMatrix()

    if heal_glow > 0:
        glPushMatrix()
        glColor4f(0, 1, 0, heal_glow / 15.0)
        glutSolidSphere(90, 14, 14)
        glPopMatrix()

    glPopMatrix()

# ================= ENEMY TANK MODEL =================
def draw_enemy_tank():
    glPushMatrix()

    # --- Main body ---
    glColor3f(0.55, 0.15, 0.15)  # dark red
    glScalef(1.4, 1.0, 0.4)
    glutSolidCube(30)
    glScalef(1/1.4, 1/1.0, 1/0.4)

    # --- Turret ---
    glPushMatrix()
    glTranslatef(5, 0, 10)
    glColor3f(0.4, 0.1, 0.1)
    glutSolidCube(18)
    glPopMatrix()

    # --- Cannon ---
    glPushMatrix()
    glTranslatef(20, 0, 10)
    glRotatef(90, 0, 1, 0)
    glColor3f(0.8, 0.8, 0.8)
    gluCylinder(gluNewQuadric(), 3, 3, 22, 10, 10)
    glPopMatrix()

    glPopMatrix()


def draw_helicopter(is_enemy=True, scale=0.4, destroy_timer=0, alive=True):
    glPushMatrix()
    glScalef(scale, scale, scale)

    # ✅ FIX 1: Only draw helicopter if it's alive
    if alive:
        # Body
        if is_enemy:
            glColor3f(1, 0, 0)   # red enemy
        else:
            glColor3f(0, 1, 0)   # green friendly
        
        glScalef(1.5, 1, 0.6)
        glutSolidCube(80)
        glScalef(1/1.5, 1, 1/0.6)

        # Cockpit
        glPushMatrix()
        if is_enemy:
            glColor3f(0.8, 0.2, 0.2)
        else:
            glColor3f(0.2, 0.8, 0.2)
        glTranslatef(50, 0, 10)
        glScalef(0.6, 0.8, 0.5)
        glutSolidCube(60)
        glPopMatrix()

        # Tail
        glPushMatrix()
        if is_enemy:
            glColor3f(0.7, 0.1, 0.1)
        else:
            glColor3f(0.1, 0.7, 0.1)
        glTranslatef(-100, 0, 0)
        glScalef(2.5, 0.3, 0.3)
        glutSolidCube(40)
        glPopMatrix()

        # Rotor mast
        glPushMatrix()
        glColor3f(0.3, 0.3, 0.3)
        glTranslatef(0, 0, 40)
        gluCylinder(gluNewQuadric(), 6, 6, 25, 10, 10)
        glPopMatrix()

        # Main rotor (rotating)
        glPushMatrix()
        glColor3f(0.1, 0.1, 0.1)
        glTranslatef(0, 0, 65)
        glRotatef(rotor_angle, 0, 0, 1)
        glScalef(3.5, 0.15, 0.05)
        glutSolidCube(80)
        glPopMatrix()

    # ✅ FIX 1: Draw destruction effect for this specific helicopter
    if destroy_timer > 0:
        glPushMatrix()
        glColor3f(1.0, 0.5, 0.0)
        size = 50 + (30 - destroy_timer) * 3
        glutSolidSphere(size, 16, 16)
        glPopMatrix()

    glPopMatrix()


# FIX 1: Anti-collision separation function
def apply_separation(x, y, others):
    for ox, oy, _ in others:
        dx = x - ox
        dy = y - oy
        dist = math.sqrt(dx*dx + dy*dy) + 0.001
        if dist < SAFE_HELI_DISTANCE:
            # Repulsion force
            force = 2.0 * (SAFE_HELI_DISTANCE - dist) / SAFE_HELI_DISTANCE
            x += (dx / dist) * force
            y += (dy / dist) * force
    return x, y


# Modified to accept height parameter
def draw_searchlight_cone(height):
    glColor4f(1.0, 1.0, 0.2, 0.6)  # transparent yellow

    radius = 120
    slices = 20

    glBegin(GL_TRIANGLES)
    for i in range(slices):
        angle1 = (2 * math.pi / slices) * i
        angle2 = (2 * math.pi / slices) * (i + 1)

        x1 = radius * math.cos(angle1)
        y1 = radius * math.sin(angle1)
        x2 = radius * math.cos(angle2)
        y2 = radius * math.sin(angle2)

        glVertex3f(0, 0, 0)
        glVertex3f(x1, y1, -height)
        glVertex3f(x2, y2, -height)
    glEnd()


def draw_text(x, y, text):
    # Don't change projection here - assume we're already in 2D ortho mode
    glColor3f(1, 1, 1)
    glRasterPos2f(x, y)
    for character in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(character))

def draw_mode_indicator():
    # Shows whether player is in Air or Ground mode
    draw_text(20, 710, f"Mode: {player_mode.upper()}")

def draw_points():
    # Shows current points (score)
    draw_text(20, 680, f"Points: {score}")

def draw_threat_warning():
    # Checks distance to enemies and warns if close
    for heli in enemy_helis:
        if heli["alive"]:
            dx = heli["pos"][0] - player_pos[0]
            dy = heli["pos"][1] - player_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 200:  # within danger range
                glColor3f(1, 0, 0)
                draw_text(20, 650, "!! ENEMY NEARBY !!")
                break



def is_player_in_cone(heli_world_pos, cone_yaw_deg):
    hx, hy, hz = heli_world_pos
    px, py, pz = player_pos

    vx = px - hx
    vy = py - hy
    vz = pz - hz

    if vz > -20:
        return False

    max_dist = 220
    dist2 = vx*vx + vy*vy + vz*vz
    if dist2 > max_dist * max_dist:
        return False

    rad = math.radians(cone_yaw_deg)
    dx = math.cos(rad)
    dy = math.sin(rad)

    horiz_len = math.sqrt(vx*vx + vy*vy) + 0.0001
    ux = vx / horiz_len
    uy = vy / horiz_len

    dot = ux*dx + uy*dy
    cone_half_angle = math.cos(math.radians(40))

    if dot > cone_half_angle:
        return True

    depth = abs(vz)
    cone_radius_at_depth = (depth / 180.0) * 120

    if horiz_len <= cone_radius_at_depth:
        return True

    return False


def spawn_enemy_bullet(hx, hy, hz):
    px, py, pz = player_pos
    dx = px - hx
    dy = py - hy
    dz = pz - hz

    length = math.sqrt(dx*dx + dy*dy + dz*dz) + 0.0001
    speed = 10

    vx = (dx / length) * speed
    vy = (dy / length) * speed
    vz = (dz / length) * speed

    enemy_bullets.append([hx, hy, hz, vx, vy, vz])

def spawn_tank_bullet(tx, ty, tz, yaw):
    speed = 14
    rad = math.radians(yaw)

    vx = math.cos(rad) * speed
    vy = math.sin(rad) * speed

    enemy_tank_bullets.append([
        tx + math.cos(rad) * 35,
        ty + math.sin(rad) * 35,
        tz + 15,
        vx, vy, 0
    ])

def update_and_draw_enemy_bullets():
    glColor3f(1.0, 0.3, 0.0)
    to_remove = []

    for b in enemy_bullets:
        b[0] += b[3]
        b[1] += b[4]
        b[2] += b[5]

        glPushMatrix()
        glTranslatef(b[0], b[1], b[2])
        glutSolidSphere(15, 16, 16)
        glPopMatrix()

        # Hit player
        dx = b[0] - player_pos[0]
        dy = b[1] - player_pos[1]
        dz = b[2] - player_pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < 30:
            player_hit()
            to_remove.append(b)

        if b[2] < -100 or abs(b[0]) > 1000 or abs(b[1]) > 1000:
            to_remove.append(b)

    for b in to_remove:
        enemy_bullets.remove(b)

def update_and_draw_tank_bullets():
    global player_health

    glColor3f(1.0, 0.6, 0.1)
    remove_list = []

    for b in enemy_tank_bullets:
        b[0] += b[3]
        b[1] += b[4]

        glPushMatrix()
        glTranslatef(b[0], b[1], b[2])
        glutSolidSphere(14, 12, 12)
        glPopMatrix()

        # Hit player (POWERFUL DAMAGE)
        dx = b[0] - player_pos[0]
        dy = b[1] - player_pos[1]
        dz = b[2] - player_pos[2]

        if math.sqrt(dx*dx + dy*dy + dz*dz) < 35:
            player_hit()
            player_health -= 15   # extra damage
            remove_list.append(b)

        # Out of bounds
        if abs(b[0]) > 1200 or abs(b[1]) > 1200:
            remove_list.append(b)

    for b in remove_list:
        enemy_tank_bullets.remove(b)

def drop_crate(x, y, z):
    crate_type = "health" if random.random() < 0.5 else "ammo"
    crates.append([x, y, z, crate_type])


def update_and_draw_crates():
    global player_health, player_ammo, heal_glow, hud_flash
    to_remove = []

    for c in crates:
        # Drop animation
        c[2] -= 5

        glPushMatrix()
        # Both crates look different but behave the same
        if c[3] == "health":
            glColor3f(0, 1, 0)   # green crate
        else:
            glColor3f(0, 0, 1)   # blue crate
        glTranslatef(c[0], c[1], c[2])
        glutSolidCube(25)
        glPopMatrix()

        # Stop falling at ground level
        if c[2] <= 0:
            c[2] = 0

        # Collision check with player
        dx = c[0] - player_pos[0]
        dy = c[1] - player_pos[1]
        if abs(dx) < 30 and abs(dy) < 30 and c[2] == 0:
            # ✅ Same logic for both crate types
            player_health += 10
            if player_health > 100:
                player_health = 100
            heal_glow = 8
            hud_flash = 10
            to_remove.append(c)

    # Remove collected crates
    for c in to_remove:
        crates.remove(c)



def player_heal():
    global heal_glow, player_health
    heal_glow = 8
    player_health += 10
    if player_health > 100:
        player_health = 100


def switch_mode():
    global player_mode, is_switching
    if not is_switching:
        player_mode = "air" if player_mode == "ground" else "ground"
        is_switching = True


def update_transformation():
    global switch_anim, is_switching
    if is_switching:
        switch_anim += 0.05
        if switch_anim >= 1:
            switch_anim = 0
            is_switching = False


def move_player(key):
    global player_yaw

    speed = move_speed_ground if player_mode == "ground" else move_speed_air
    rot_speed = 4  # turning speed

    # Convert yaw to direction vector
    rad = math.radians(player_yaw)
    forward_x = math.cos(rad)
    forward_y = math.sin(rad)

    # Proposed new position
    new_x, new_y = player_pos[0], player_pos[1]

    if key == 'w':  # forward
        new_x += forward_x * speed
        new_y += forward_y * speed
    elif key == 's':  # backward
        new_x -= forward_x * speed
        new_y -= forward_y * speed
    elif key == 'a':  # turn left
        player_yaw += rot_speed
    elif key == 'd':  # turn right
        player_yaw -= rot_speed

    # Only move if no collision with boundary, trees, or obstacles
    if not collides(new_x, new_y):
        player_pos[0], player_pos[1] = new_x, new_y

    # Vertical movement in air mode
    if player_mode == "air":
        if key == 'q':
            player_pos[2] += speed * 0.6
        elif key == 'e':
            player_pos[2] -= speed * 0.6

    if player_pos[2] < 0:
        player_pos[2] = 0



def shoot_bullet():
    global ground_cooldown, air_cooldown, player_ammo, gun_angle
    if player_ammo <= 0:
        return

    # Direction from yaw and pitch
    yaw_rad = math.radians(player_yaw)
    pitch_rad = math.radians(gun_pitch)
    dx = math.cos(yaw_rad) * math.cos(pitch_rad)
    dy = math.sin(yaw_rad) * math.cos(pitch_rad)
    dz = math.sin(pitch_rad)

    if player_mode == "ground":
        if ground_cooldown == 0:
            speed = 25
            player_bullets.append([
                player_pos[0] + 40 * math.cos(yaw_rad),
                player_pos[1] + 40 * math.sin(yaw_rad),
                player_pos[2] + 20,
                dx * speed, dy * speed, dz * 0  # ground bullets stay mostly horizontal
            ])
            ground_cooldown = 15
            player_ammo -= 1
            gun_angle = 10.0
    else:
        if air_cooldown == 0:
            speed = 30
            player_bullets.append([
                player_pos[0] + 40 * math.cos(yaw_rad),
                player_pos[1] + 40 * math.sin(yaw_rad),
                player_pos[2] + 20,
                dx * speed, dy * speed, dz * 10  # air bullets can go up/down
            ])
            air_cooldown = 10
            player_ammo -= 1
            gun_angle = 10.0


def update_player_bullets():
    global player_bullets, ground_cooldown, air_cooldown, score

    if ground_cooldown > 0:
        ground_cooldown -= 1
    if air_cooldown > 0:
        air_cooldown -= 1

    glColor3f(1, 1, 0.2)
    remove_list = []

    for b in player_bullets:
        b[0] += b[3]
        b[1] += b[4]
        b[2] += b[5]

        glPushMatrix()
        glTranslatef(b[0], b[1], b[2])
        glutSolidSphere(10, 10, 10)
        glPopMatrix()

        # ================= HELICOPTER COLLISION =================
        for heli in enemy_helis:
            if not heli["alive"]:
                continue

            hx, hy, hz = heli["pos"]
            dx = b[0] - hx
            dy = b[1] - hy
            dz = b[2] - hz

            if math.sqrt(dx*dx + dy*dy + dz*dz) < 50:
                heli["destroy_timer"] = 30
                heli["alive"] = False
                score += 20
                remove_list.append(b)
                break

        if b in remove_list:
            continue

        # ================= TANK COLLISION (THIS IS THE FIX) =================
        for tank in enemy_tanks:
            if not tank["alive"]:
                continue

            tx, ty, tz = tank["pos"]

            dx = b[0] - tx
            dy = b[1] - ty
            dz = b[2] - (tz + 20)   # tank center height

            if math.sqrt(dx*dx + dy*dy + dz*dz) < 60:  # 2× scaled tank
                tank["health"] -= 20
                remove_list.append(b)

                if tank["health"] <= 0:
                    tank["alive"] = False
                    score += 30
                break

        if b in remove_list:
            continue

        # ================= FRIENDLY HELI COLLISION =================
        if friendly_heli["alive"]:
            fx, fy, fz = friendly_heli["pos"]
            dx = b[0] - fx
            dy = b[1] - fy
            dz = b[2] - fz

            if math.sqrt(dx*dx + dy*dy + dz*dz) < 50:
                friendly_heli["alive"] = False
                remove_list.append(b)
                continue

        # ================= OUT OF BOUNDS =================
        if abs(b[0]) > GRID_LENGTH + 500 or abs(b[1]) > GRID_LENGTH + 500 or b[2] < -50 or b[2] > 800:
            remove_list.append(b)

    for b in remove_list:
        if b in player_bullets:
            player_bullets.remove(b)

def respawn_enemy_heli(heli):
    # Spawn far outside player camera range
    angle = random.uniform(0, 2 * math.pi)
    distance = 900  # outside view

    heli["pos"] = [
        player_pos[0] + math.cos(angle) * distance,
        player_pos[1] + math.sin(angle) * distance,
        random.randint(180, 260)
    ]

    heli["target"] = [
    random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
    random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
    random.randint(180, 260)
   ]


    heli["alive"] = True
    heli["destroy_timer"] = 0
    heli["fire_timer"] = random.randint(0, 25)
    heli["detected"] = False

def draw_health_bar(x, y, width, height, health):
    glColor3f(0.3, 0.3, 0.3)  # background
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glVertex2f(x + width, y + height)
    glVertex2f(x, y + height)
    glEnd()

    # ✅ Flash green if hud_flash is active
    if hud_flash > 0:
        glColor3f(0.0, 1.0, 0.0)  # bright green flash
    else:
        glColor3f(0, 1, 0)        # normal green health

    fill = (health / 100) * width
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + fill, y)
    glVertex2f(x + fill, y + height)
    glVertex2f(x, y + height)
    glEnd()


def draw_ammo_bar(x, y, width, height, ammo):
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glVertex2f(x + width, y + height)
    glVertex2f(x, y + height)
    glEnd()

    glColor3f(1, 1, 0)  # yellow ammo
    fill = min(ammo / 100, 1.0) * width
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + fill, y)
    glVertex2f(x + fill, y + height)
    glVertex2f(x, y + height)
    glEnd()

def player_hit():
    global hit_flash, player_health, game_over
    hit_flash = 10
    player_health -= 10
    if player_health <= 0:
        player_health = 0
        game_over = True



def update_effects():
    global hit_flash, heal_glow , hud_flash
    if hit_flash > 0:
        hit_flash -= 1
    if heal_glow > 0:
        heal_glow -= 1
    if hud_flash > 0: 
        hud_flash -= 1


def keyboardListener(key, x, y):
    global camera_mode, game_over, win, gun_pitch, paused
    key = key.decode('utf-8').lower()

    # If game ended (win or game_over), allow ESC to exit and R to restart
    if game_over or win:
        if key == '\x1b':  # ESC
            glutLeaveMainLoop()
        elif key == 'r':   # Restart
            reset_game()
        return

    # Restart anytime
    if key == 'r':
        reset_game()
        return

    # Pause toggle via keyboard (optional shortcut)
    if key == 'p':
        paused = not paused
        return

    # Movement and gameplay controls
    move_player(key)

    if key == 't':  # Transform mode
        switch_mode()
    if key == 'f':  # Fire
        shoot_bullet()
    if key == 'c':  # Toggle camera mode
        camera_mode = "first" if camera_mode == "third" else "third"

    # Gun pitch control (unused keys chosen: i/k)
    if key == 'i':  # pitch up
        gun_pitch = min(gun_pitch + 3.0, 45.0)
    if key == 'k':  # pitch down
        gun_pitch = max(gun_pitch - 3.0, -20.0)



def specialKeyListener(key, x, y):
    global camera_pos
    cx, cy, cz = camera_pos
    if key == GLUT_KEY_LEFT:
        cx -= 20
    if key == GLUT_KEY_RIGHT:
        cx += 20
    if key == GLUT_KEY_UP:
        cz += 20
    if key == GLUT_KEY_DOWN:
        cz -= 20
    camera_pos = (cx, cy, cz)


# ✅ FIX 3: Changed mouse controls
def mouseListener(button, state, x, y):
    global paused
    if state != GLUT_DOWN:
        return

    # Convert window coords to HUD coords
    hud_x, hud_y = x, 800 - y

    # Pause button
    if (UI_PAUSE_BTN["x"] <= hud_x <= UI_PAUSE_BTN["x"] + UI_PAUSE_BTN["w"] and
        UI_PAUSE_BTN["y"] <= hud_y <= UI_PAUSE_BTN["y"] + UI_PAUSE_BTN["h"]):
        paused = not paused
        return

    # Exit button
    if (UI_EXIT_BTN["x"] <= hud_x <= UI_EXIT_BTN["x"] + UI_EXIT_BTN["w"] and
        UI_EXIT_BTN["y"] <= hud_y <= UI_EXIT_BTN["y"] + UI_EXIT_BTN["h"]):
        glutLeaveMainLoop()
        return

    # 🔥 LEFT CLICK = FIRE
    if button == GLUT_LEFT_BUTTON:
        shoot_bullet()

    # 🔁 RIGHT CLICK = TRANSFORM
    elif button == GLUT_RIGHT_BUTTON:
        camera_mode = "first" if camera_mode == "third" else "third"

def idle():
    global rotor_angle, heli_time_friend, search_angle, crate_drop_timer
    global gun_angle, game_over, win, paused

    # ✅ Respect pause: freeze updates but still redraw
    if paused:
        glutPostRedisplay()
        return

    # ✅ Timer-based game over
    elapsed = get_elapsed_seconds()
    if not game_over and not win and elapsed >= TIMER_LIMIT_SECONDS:
        if score < 100 and player_health > 0:
            game_over = True

    # ✅ Win condition
    if not win and score >= 100 and player_health > 0:
        win = True

    # Rotor and friendly heli animation
    rotor_angle = (rotor_angle + 10) % 360
    heli_time_friend += 0.02

    # Searchlight oscillation
    search_angle += 1.5
    if search_angle > 45 or search_angle < -45:
        search_angle *= -1

    # Crate timer
    crate_drop_timer += 1

    # Transform and effects
    update_transformation()
    update_effects()

    # Enemy heli explosion timers and respawn
    for heli in enemy_helis:
        if heli["destroy_timer"] > 0:
            heli["destroy_timer"] -= 1
        if heli["destroy_timer"] == 0 and heli["alive"] == False:
            respawn_enemy_heli(heli)

    # ✅ Friendly heli movement and crate drops
    update_friendly_heli_and_crates()

    # Gun recoil animation
    if gun_angle > 0:
        gun_angle -= 1

    # Redraw
    glutPostRedisplay()


def draw_crosshair():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(1, 1, 1)  # white crosshair
    cx, cy = 500, 400   # screen center

    glBegin(GL_LINES)
    glVertex2f(cx - 10, cy)
    glVertex2f(cx + 10, cy)
    glVertex2f(cx, cy - 10)
    glVertex2f(cx, cy + 10)
    glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_hud():
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # ===== LEFT SIDE TEXT =====
    # Score & Timer
    draw_text(20, 770, f"Score: {score}")
    elapsed = get_elapsed_seconds()
    remaining = max(0, TIMER_LIMIT_SECONDS - elapsed)
    draw_text(20, 740, f"Time Left: {remaining}s")

    # Mode Indicator
    draw_text(20, 710, f"Mode: {player_mode.upper()}")

    # Health
    draw_text(20, 680, f"Health: {player_health}")
    draw_health_bar(20, 660, 200, 15, player_health)

    # Ammo
    draw_text(20, 630, f"Ammo: {player_ammo}")
    draw_ammo_bar(20, 610, 200, 15, player_ammo)

    # Points
    draw_text(20, 580, f"Points: {score}")

    # Enemy Threat Warning
    for heli in enemy_helis:
        if heli["alive"]:
            dx = heli["pos"][0] - player_pos[0]
            dy = heli["pos"][1] - player_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 200:  # within danger range
                glColor3f(1, 0, 0)
                draw_text(20, 550, "!! ENEMY NEARBY !!")
                break

    # ===== RIGHT SIDE BUTTONS =====
    # Pause Button
    glColor3f(0.5, 0.5, 0.5)
    glBegin(GL_QUADS)
    glVertex2f(UI_PAUSE_BTN["x"], UI_PAUSE_BTN["y"])
    glVertex2f(UI_PAUSE_BTN["x"] + UI_PAUSE_BTN["w"], UI_PAUSE_BTN["y"])
    glVertex2f(UI_PAUSE_BTN["x"] + UI_PAUSE_BTN["w"], UI_PAUSE_BTN["y"] + UI_PAUSE_BTN["h"])
    glVertex2f(UI_PAUSE_BTN["x"], UI_PAUSE_BTN["y"] + UI_PAUSE_BTN["h"])
    glEnd()
    draw_text(UI_PAUSE_BTN["x"] + 10, UI_PAUSE_BTN["y"] + 10,
              "PAUSE" if not paused else "PLAY")

    # Exit Button
    glColor3f(0.8, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(UI_EXIT_BTN["x"], UI_EXIT_BTN["y"])
    glVertex2f(UI_EXIT_BTN["x"] + UI_EXIT_BTN["w"], UI_EXIT_BTN["y"])
    glVertex2f(UI_EXIT_BTN["x"] + UI_EXIT_BTN["w"], UI_EXIT_BTN["y"] + UI_EXIT_BTN["h"])
    glVertex2f(UI_EXIT_BTN["x"], UI_EXIT_BTN["y"] + UI_EXIT_BTN["h"])
    glEnd()
    draw_text(UI_EXIT_BTN["x"] + 12, UI_EXIT_BTN["y"] + 10, "X")

    # ===== RESTORE 3D PROJECTION =====
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)


#friendly helicopter behaviour
def update_friendly_heli_and_crates():
    global friendly_crate_timer
    if not friendly_heli["alive"]:
        return

    # Simple movement toward target
    x, y, z = friendly_heli["pos"]
    tx, ty, tz = friendly_heli["target"]
    dx, dy, dz = tx - x, ty - y, tz - z
    dist = math.sqrt(dx*dx + dy*dy + dz*dz) + 0.001
    speed = 1.6
    x += (dx / dist) * speed
    y += (dy / dist) * speed
    z += (dz / dist) * speed
    friendly_heli["pos"] = [x, y, z]

    # Pick new target when close
    if dist < 25:
        friendly_heli["target"] = [
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
            random.randint(180, 240)
        ]

    # Drop health crates periodically only if friendly heli is alive
    friendly_crate_timer += 1
    if friendly_crate_timer >= FRIENDLY_CRATE_INTERVAL:
        friendly_crate_timer = 0
        hx, hy, hz = friendly_heli["pos"]
        drop_crate(hx, hy, hz)



def showScreen():
    global crate_drop_timer

    # ✅ Handle win/lose states first
    if win:
        show_win()
        return

    if game_over:
        show_game_over()
        return

    # ✅ Normal gameplay rendering
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, 1000, 800)

    setupCamera()
    draw_grid_floor(GRID_LENGTH)
    draw_arena_walls(size=GRID_LENGTH, height=180)

    # Draw trees
    for t in trees:
        draw_tree(t[0], t[1])

    # Draw obstacles
    for o in obstacles:
        draw_obstacle(o[0], o[1], o[2], o[3])

    # ================= DRAW ENEMY TANKS =================
# ================= ENEMY TANK DETECTION =================
# ================= ENEMY TANK DETECTION + FIRE =================
    for tank in enemy_tanks:
        if not tank["alive"]:
            continue

        tx, ty, tz = tank["pos"]

        dx = player_pos[0] - tx
        dy = player_pos[1] - ty
        distance = math.sqrt(dx*dx + dy*dy)

        DETECTION_RANGE = 350

        tank["fire_timer"] += 1

        if distance < DETECTION_RANGE:
            # Aim at player
            tank["yaw"] = math.degrees(math.atan2(dy, dx))

            # Fire cannon every ~80 frames
            if tank["fire_timer"] >= 80:
                spawn_tank_bullet(tx, ty, tz, tank["yaw"])
                tank["fire_timer"] = 0

        # Draw tank
        glPushMatrix()
        glTranslatef(tx, ty, tz + 10)
        glRotatef(tank["yaw"], 0, 0, 1)
        glScalef(2.0, 2.0, 2.0)  
        draw_enemy_tank()
        glPopMatrix()


    # Draw player (only in third-person mode)
    if camera_mode == "third":
        draw_player_vehicle()

    # Friendly helicopter
    if friendly_heli["alive"]:
        glPushMatrix()
        glTranslatef(friendly_heli["pos"][0],
                     friendly_heli["pos"][1],
                     friendly_heli["pos"][2])
        draw_helicopter(is_enemy=False, scale=0.4, destroy_timer=0, alive=True)
        glPopMatrix()

    # Enemy helicopters
    any_enemy_detected = False
    for heli in enemy_helis:
        if not heli["alive"]:
            continue

        # Current position and target
        x, y, z = heli["pos"]
        tx, ty, tz = heli["target"]

        # Movement toward target
        dx, dy, dz = tx - x, ty - y, tz - z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz) + 0.001
        speed = 2.0
        x += (dx / dist) * speed
        y += (dy / dist) * speed
        z += (dz / dist) * speed

        # Bounce off boundary → pick new random target
        if x < -GRID_LENGTH + MARGIN or x > GRID_LENGTH - MARGIN:
            heli["target"][0] = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)
        if y < -GRID_LENGTH + MARGIN or y > GRID_LENGTH - MARGIN:
            heli["target"][1] = random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN)

        # Pick new target when close
        if dist < 20:
            heli["target"] = [
                random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
                random.randint(-GRID_LENGTH + MARGIN, GRID_LENGTH - MARGIN),
                random.randint(180, 260)
            ]

        # Update heli position
        heli["pos"] = [x, y, z]
        # ================= ENEMY SHOOTING =================
        heli["fire_timer"] += 1

        hx, hy, hz = heli["pos"]
        px, py, pz = player_pos

        dx = px - hx
        dy = py - hy
        dz = pz - hz
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Shoot every ~60 frames if player is near
        if is_player_in_cone(heli["pos"], search_angle) and heli["fire_timer"] >= 60:

            spawn_enemy_bullet(hx, hy, hz)
            heli["fire_timer"] = 0


        # Draw enemy heli
        glPushMatrix()
        glTranslatef(x, y, z)
        draw_helicopter(is_enemy=True, scale=0.4,
                        destroy_timer=heli["destroy_timer"],
                        alive=heli["alive"])
        glPopMatrix()
        # ===== SEARCHLIGHT CONE =====
        glPushMatrix()
        glTranslatef(x, y, z - 10)   # start under helicopter
        glRotatef(search_angle, 0, 0, 1)
        draw_searchlight_cone(z)    # cone height
        glPopMatrix()

            

    # Enemy bullets
    update_and_draw_enemy_bullets()
    update_and_draw_tank_bullets()


    # Player bullets
    update_player_bullets()

    # Crates
    update_and_draw_crates()

    # ✅ Diamonds
    update_and_draw_diamonds()

    # ✅ HUD (score, timer, pause/play, exit, crosshair)
    draw_hud()

    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Guardian: Sky & Ground - 4 Enemy Helicopters")

    # Enable depth testing and blending for proper 3D rendering and transparency
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glClearColor(0.53, 0.81, 0.92, 1.0)

    glutDisplayFunc(showScreen)
    #########
    reset_game()
    spawn_diamonds()
    ########
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()


if __name__ == "__main__":
    main()