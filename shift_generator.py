import datetime
from datetime import timedelta, date
from calendar import monthrange
import random
from collections import defaultdict, deque

# Importar referencias a la BD desde app (asumiendo que están inicializadas allí)
# Si esto causa problemas de importación circular, moveremos la inicialización aquí.
try:
    from app import users_collection, events_collection, es_dia_habil, FESTIVOS_DATES
except ImportError:
    # Fallback para pruebas si app no está disponible
    print("Warning: Could not import from app, running in standalone mode or mocks needed.")
    users_collection = None
    events_collection = None
    es_dia_habil = lambda d: d.weekday() < 5
    FESTIVOS_DATES = set()

class ShiftGenerator:
    def __init__(self, debug=True):
        self.debug = debug
        self.logs = []
        self.users = []
        self.existing_events = {} # Map (date_str, user_id) -> event_type
        self.generated_events = []
        self.warnings = [] # Store structural warnings
        
        # DEFINICIÓN DE REGLAS Y PARAMETROS
        self.REQ_CADE_30 = 3
        self.REQ_CADE_50 = 4
        self.REQ_TARDES = 4
        self.REQ_MAIL = 1
        
        # WEEKLY STABILITY TRACKER (Persists between generate calls)
        self.last_assignments = {} # UserID -> Role (Daily stickiness)
        self.last_week_roles = {}   # UserID -> Role (Projected/Dominant role of previous week)
        self.current_week_roles = {} # UserID -> Role (Roles assigned this week)
        
        # Identificadores especiales (nombres exactos o IDs, ajustar según DB real)
        # TODO: Idealmente estos deberían venir de configuración o tags en DB
        self.USER_DEPENDENCY_TRIGGER = ["Celia Martínez"] # Nombres complets
        self.USER_REDUCTION = ["Izarbe", "Rodrigo"] # Substrings o nombres
        
    def set_requirements(self, c30, c50, tardes, mail=1):
        """Allows overriding default staff requirements."""
        self.REQ_CADE_30 = int(c30)
        self.REQ_CADE_50 = int(c50)
        self.REQ_TARDES = int(tardes)
        self.REQ_MAIL = int(mail)
        self.log(f"Requirements Updated: C30={self.REQ_CADE_30}, C50={self.REQ_CADE_50}, Tardes={self.REQ_TARDES}, Mail={self.REQ_MAIL}")
        
    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.logs.append(log_msg)
        if self.debug:
            print(log_msg)

    def fetch_data(self):
        """Carga usuarios y sus skills."""
        if users_collection is None:
            self.log("ERROR: No database connection.")
            return

        # Cargar usuarios filtrando por visibilidad Y puesto 'TS'
        self.users = list(users_collection.find({
            "visible_calendario": {"$ne": False},
            "puesto": "TS"
        }))
        self.log(f"Loaded {len(self.users)} TS users.")
        
        # Normalizar skills (si no existen, dejar lista vacía)
        for u in self.users:
            if "skills" not in u:
                u["skills"] = []
                
        # TODO: Para PROBAR ahora, asignaré skills ficticias si no existen
        # Esto debería borrarse en producción o gestionarse desde UI
        self._mock_skills_data()

    def _mock_skills_data(self):
        """Asigna skills temporales para probar el algoritmo si no están en DB."""
        # Detectar candidatos para "Tarde" (simulado para este ejemplo)
        # En prod, filtrar por u['skills']
        count_tarde = 0
        for u in self.users:
            full_name = f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip()
            
            # Simular los 6 de tardes
            # Ajustar lógica para seleccionar 6 personas concretas si se conocen sus nombres
            if "skills" not in u: u["skills"] = []
            
            # Lógica temporal: Asignar 'Tarde' a 6 usuarios aleatorios o específicos si la lista está vacía
            # Para evitar sobrescribir datos reales cuando los haya, solo lo hacemos si nadie tiene skill Tarde
        
        tarde_users = [u for u in self.users if "Tarde" in u["skills"]]
        if not tarde_users:
            self.log("MOCK: Asignando skill 'Tarde' a los primeros 6 usuarios para testing.")
            for i in range(min(6, len(self.users))):
                if "skills" not in self.users[i]: self.users[i]["skills"] = []
                self.users[i]["skills"].append("Tarde")

    def load_existing_events(self, year, month):
        """Carga eventos existentes (Vacaciones, Bajas, etc) para no sobreescribir."""
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        query = {
            "fecha_inicio": {"$gte": start_str, "$lte": end_str}
        }
        
        events = list(events_collection.find(query))
        self.existing_events = defaultdict(dict)
        
        for e in events:
            # Expandir eventos de rango a días individuales para chequeo rápido
            f_inicio = datetime.datetime.strptime(e["fecha_inicio"], "%Y-%m-%d").date()
            f_fin = datetime.datetime.strptime(e["fecha_fin"], "%Y-%m-%d").date()
            trabajador = e["trabajador"] # Nombre completo suele ser la clave actual
            
            curr = f_inicio
            while curr <= f_fin:
                if start_date <= curr <= end_date:
                    self.existing_events[curr.strftime("%Y-%m-%d")][trabajador] = e["tipo"]
                curr += timedelta(days=1)
                
        self.log(f"Loaded existing events for {len(events)} records.")

    def get_annual_balance(self, year, exclude_start_date, exclude_end_date):
        """Calcula el balance acumulado de turnos para el año, excluyendo el mes actual."""
        if events_collection is None:
            return defaultdict(int)

        start_year = date(year, 1, 1).strftime("%Y-%m-%d")
        end_year = date(year, 12, 31).strftime("%Y-%m-%d")
        
        query = {
            "fecha_inicio": {"$gte": start_year, "$lte": end_year}
        }
        events = list(events_collection.find(query))
        
        events = list(events_collection.find(query))
        
        # Initialize dictionary of counters
        # counts[role_type][user_id] = count
        counts = defaultdict(lambda: defaultdict(int))
        
        exclude_start = exclude_start_date.strftime("%Y-%m-%d")
        exclude_end = exclude_end_date.strftime("%Y-%m-%d")
        
        for e in events:
            # Skip events in the month we are rewriting
            if exclude_start <= e["fecha_inicio"] <= exclude_end:
                continue
            
            # Count Tardes (or others if needed later)
            if e["tipo"] == "CADE Tardes":
                # Use user ID if possible, but we might only have name. 
                # Ideally we map name to ID, but current logic uses ID in counters.
                # Let's try to find user by name to get ID, or fallback to name matching if we change logic.
                # Wait, 'generate' uses 'str(u["_id"])' for keys.
                # 'e["trabajador"]' is "Nombre Apellido".
                # We need a map Name -> ID.
                pass 
                
        # To strictly match IDs used in generate(), we need to map names from DB events to IDs.
        # Since self.users is loaded, we can build a map.
        name_to_id = {f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip(): str(u["_id"]) for u in self.users}
        
        for e in events:
             if exclude_start <= e["fecha_inicio"] <= exclude_end:
                continue
             
             w_name = e["trabajador"]
             if w_name in name_to_id:
                 uid = name_to_id[w_name]
                 if e["tipo"] == "CADE Tardes":
                     counts["CADE Tardes"][uid] += 1
                 elif e["tipo"] == "Refuerzo Cade":
                     counts["Refuerzo Cade"][uid] += 1
                 elif e["tipo"] == "CADE 30":
                     counts["CADE 30"][uid] += 1
                 elif e["tipo"] == "CADE 50":
                     counts["CADE 50"][uid] += 1
                 elif e["tipo"] == "Mail":
                     counts["Mail"][uid] += 1

        return counts

    def get_available_users(self, day_str, required_skill=None):
        """Devuelve usuarios disponibles (sin Vacaciones/Baja) para un día."""
        available = []
        for u in self.users:
            full_name = f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip()
            
            # Check availability
            # Tipos de bloqueo: Vacaciones, Baja, Asuntos Propios...
            day_events = self.existing_events.get(day_str, {})
            user_event = day_events.get(full_name)
            
            if user_event and user_event != "PIAS":
                # Si tiene cualquier evento en BD (Vacaciones, Baja, CADE 30, etc) SALVO PIAS, NO está disponible
                continue
                
            # Check skill
            if required_skill and required_skill not in u.get("skills", []):
                continue
                
            available.append(u)
        return available

    def generate(self, year, month):
        self.generated_events = []
        self.log(f"Starting generation for {month}/{year}")
        
        _, last_day = monthrange(year, month)
        
        start_date_ex = date(year, month, 1)
        end_date_ex = date(year, month, last_day)
        
        # Contadores para equidad HISTÓRICA (Key: UserID, Value: Count)
        self.log("Fetching annual history for balancing...")
        all_counts = self.get_annual_balance(year, start_date_ex, end_date_ex)
        
        # Extract specific counters
        tarde_count = all_counts["CADE Tardes"]
        refuerzo_count = all_counts["Refuerzo Cade"]
        cade30_count = all_counts["CADE 30"]
        cade50_count = all_counts["CADE 50"]
        
        self.log(f"Initialized Refuerzo balance: {dict(sorted(refuerzo_count.items(), key=lambda x: x[1], reverse=True)[:5])}")
        
        # Iterar por días HÁBILES
        for day in range(1, last_day + 1):
            date_obj = date(year, month, day)
            day_str = date_obj.strftime("%Y-%m-%d")
            
            if not es_dia_habil(date_obj):
                continue
            
            # RESET on Mondays (Start of Week)
            if date_obj.weekday() == 0:
                self.last_assignments = {}
                # Rotate weekly history
                self.last_week_roles = self.current_week_roles.copy()
                self.current_week_roles = {}

            self.log(f"Processing Day: {day_str}")
            
            # Listas de control diario
            assigned_today = set() # Set of User IDs
            current_assignments = {} # UserID -> Role (for next day stickiness)
            
            # 0. ROLES FIJOS (Prioridad Absoluta)
            # Primero asignamos a quienes tienen un rol forzado ÚNICO
            avail_fixed = self.get_available_users(day_str)
            multi_role_constrained = {} # User -> List of allowed roles
            
            for u in avail_fixed:
                raw_role = u.get("fixed_shift_role")
                if not raw_role:
                    continue
                
                # Normalizar a lista y limpiar vacíos
                if isinstance(raw_role, str):
                    roles = [raw_role]
                else:
                    roles = list(raw_role) # Asumimos lista
                
                # Filtrar valores vacíos (e.g. [""])
                roles = [r for r in roles if r and r.strip()]
                
                if not roles:
                    continue

                if len(roles) == 1:
                    # CASO: 1 Rol Fijo -> Asignación Inmediata
                    role_target = roles[0]
                    
                    assigned_today.add(str(u["_id"]))

                    # Special Case: PIAS means NO EVENT
                    if role_target == "PIAS":
                        # We mark them as assigned so they don't get other jobs,
                        # but we do NOT generate an event.
                        # Also track tracking:
                        self.current_week_roles[str(u["_id"])] = "PIAS"
                    else:
                        self._add_event(u, day_str, role_target)
                        
                        # Increment counters for fixed roles too so they count towards fairness
                        if role_target == "CADE Tardes":
                             tarde_count[str(u["_id"])] += 1
                        elif role_target == "Refuerzo Cade":
                             refuerzo_count[str(u["_id"])] += 1
                        elif role_target == "CADE 30":
                             cade30_count[str(u["_id"])] += 1
                        elif role_target == "CADE 50":
                             cade50_count[str(u["_id"])] += 1
                else:
                    # CASO: Multiple Roles -> Se guarda para asignación prioritaria luego
                    multi_role_constrained[str(u["_id"])] = roles
            
            # 1. GESTIÓN DE TARDES
            # Contar cuántos ya están cubiertos por rol fijo + BD
            db_tarde_count = sum(1 for e_type in self.existing_events.get(day_str, {}).values() if e_type == "CADE Tardes")
            fixed_tarde_count = sum(1 for e in self.generated_events if e["fecha_inicio"] == day_str and e["tipo"] == "CADE Tardes")
            
            total_tarde_filled = db_tarde_count + fixed_tarde_count
            
            tarde_candidates = self.get_available_users(day_str, required_skill="Tarde")
            
            # Filtrar candidatos que ya tengan evento (manual o fijo generado)
            tarde_finalists = []
            for tc in tarde_candidates:
                uid = str(tc["_id"])
                if uid not in assigned_today:
                    # Verificar restricción multi-rol
                    if uid in multi_role_constrained:
                        if "CADE Tardes" not in multi_role_constrained[uid]:
                            continue

                    # Además verificar manuales
                    full_name = f"{tc.get('nombre', '')} {tc.get('apellidos', '')}".strip()
                    if full_name not in self.existing_events.get(day_str, {}):
                        tarde_finalists.append(tc)

            # Ordenar por Sticky (Misma tarea ayer) y luego carga
            random.shuffle(tarde_finalists)
            tarde_finalists.sort(key=lambda u: (
                0 if str(u["_id"]) in self.last_assignments and self.last_assignments[str(u["_id"])] == "CADE Tardes" else 1,
                1 if str(u["_id"]) in self.last_week_roles and self.last_week_roles[str(u["_id"])] == "CADE Tardes" else 0,
                tarde_count[str(u["_id"])]
            ))

            needed = self.REQ_TARDES - total_tarde_filled
            if needed > 0:
                if len(tarde_finalists) < needed:
                    msg = f"Faltan {needed - len(tarde_finalists)} personas para TARDES el {day_str}. (Disponibles: {len(tarde_finalists)})"
                    self.log(f"CRITICAL WARNING: {msg}")
                    self.warnings.append({"date": day_str, "type": "TARDES", "message": msg, "severity": "critical"})
                    chosen_tardes = tarde_finalists
                else:
                    chosen_tardes = tarde_finalists[:needed]
                
                for u in chosen_tardes:
                    self._add_event(u, day_str, "CADE Tardes")
                    user_id = str(u["_id"])
                    assigned_today.add(user_id)
                    current_assignments[user_id] = "CADE Tardes"
                    tarde_count[user_id] += 1

            # 2. FLEXIBILIDAD (Requiere Refuerzo)
            # 2. FLEXIBILIDAD (Requiere Refuerzo)
            need_refuerzo = False
            absence_types = ["Vacaciones", "Baja", "Ausencia", "Ausente", "Baja Médica"]
            
            for u in self.users:
                full_name = f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip()
                skills = u.get("skills", [])
                
                # Check constraints logic: If user with Flex/Reduccion is WORKING today
                if "Flexibilidad" in skills or "Reducción" in skills:
                    day_events = self.existing_events.get(day_str, {})
                    user_status = day_events.get(full_name)
                    
                    # If user has an absence event, they are NOT working -> No Refuerzo needed for them
                    if user_status in absence_types:
                        continue
                        
                    # If they have no event (Available) or legitimate work event (CADE 30 manual) -> They are working
                    need_refuerzo = True
                    break
            
            if need_refuerzo:
                 # Verificar si ya existe Refuerzo (por rol fijo, generado o MANUAL en DB)
                has_refuerzo = False
                
                # 1. Check generated (Fixed Roles)
                events_today = [e for e in self.generated_events if e["fecha_inicio"] == day_str]
                for e in events_today:
                    if "Refuerzo" in e["tipo"]:
                        has_refuerzo = True
                        break
                
                # 2. Check existing Manual/DB events
                if not has_refuerzo:
                    db_refuerzo_count = sum(1 for e_type in self.existing_events.get(day_str, {}).values() if e_type == "Refuerzo Cade")
                    if db_refuerzo_count > 0:
                        has_refuerzo = True
                
                if not has_refuerzo:
                    # Buscar candidato
                    candidates = [u for u in self.get_available_users(day_str) if str(u["_id"]) not in assigned_today]
                    
                    # Filtrar restricciones de rol (si alguien tiene vetado el Refuerzo)
                    valid_candidates = []
                    for c in candidates:
                         uid = str(c["_id"])
                         if uid in multi_role_constrained and "Refuerzo Cade" not in multi_role_constrained[uid]:
                             continue
                         valid_candidates.append(c)

                    if valid_candidates:
                        # Shuffle first to break deterministic ties
                        random.shuffle(valid_candidates)
                        valid_candidates.sort(key=lambda u: (
                            0 if str(u["_id"]) in self.last_assignments and self.last_assignments[str(u["_id"])] == "Refuerzo Cade" else 1,
                            1 if str(u["_id"]) in self.last_week_roles and self.last_week_roles[str(u["_id"])] == "Refuerzo Cade" else 0,
                            refuerzo_count[str(u["_id"])]
                        ))
                        chosen = valid_candidates[0]
                        self._add_event(chosen, day_str, "Refuerzo Cade")
                        uid = str(chosen["_id"])
                        assigned_today.add(uid)
                        current_assignments[uid] = "Refuerzo Cade"
                        refuerzo_count[uid] += 1
                    else:
                        self.log(f"WARNING: No candidate for Flexibilidad (Refuerzo) on {day_str}")

            # 4. RELLENO (CADE 30, CADE 50, MAIL, BACKOFFICE)
            # Helper to check if user can do role (if restricted)
            def can_do(uid, role):
                if uid in multi_role_constrained:
                    return role in multi_role_constrained[uid]
                return True
            
            # Helper to check mail skill (Compatible with both Tag and Fixed Role)
            def has_mail_skill(u):
                # 1. Check Skill Tag
                if "Mail" in u.get("skills", []):
                    return True
                # 2. Check Fixed Role (Backwards compatibility)
                roles = u.get("fixed_shift_role", [])
                if isinstance(roles, str): roles = [roles]
                if "Mail" in roles:
                    return True
                return False

            # Helper to pick best candidate
            def pick_candidate_key(u, role_target):
                candidates = [u] # Dummy wrapper
                # We reuse the logic but return the key tuple instead of sorting a list

                # Prioritize: 1. Restricted Users (0), 2. Sticky Users (0)
                
                # Determine metric based on role
                sort_metric = 0
                uid = str(u["_id"])
                if role_target == "CADE 30": sort_metric = cade30_count[uid]
                elif role_target == "CADE 50": sort_metric = cade50_count[uid]
                
                return (
                    0 if uid in multi_role_constrained else 1,
                    0 if uid in self.last_assignments and self.last_assignments[uid] == role_target else 1,
                    1 if uid in self.last_week_roles and self.last_week_roles[uid] == role_target else 0,
                    sort_metric
                )

            remaining = [u for u in self.get_available_users(day_str) if str(u["_id"]) not in assigned_today]
            random.shuffle(remaining) 
            
            self.log(f"   [Debug] Remaining Users for Phase 4: {len(remaining)}")

            # --- CADE 30 ---
            db_30_count = sum(1 for e_type in self.existing_events.get(day_str, {}).values() if e_type == "CADE 30")
            gen_30_count = sum(1 for e in self.generated_events if e["fecha_inicio"] == day_str and e["tipo"] == "CADE 30")
            filled_30 = db_30_count + gen_30_count

            needed_30 = self.REQ_CADE_30 - filled_30
            self.log(f"   [Debug] CADE 30 Needed: {needed_30}. Pool size: {len(remaining)}")

            remaining.sort(key=lambda u: pick_candidate_key(u, "CADE 30"))

            while filled_30 < self.REQ_CADE_30 and remaining:
                # Re-sort occasionally or just pick first valid
                # Since list is already sorted by fairness, we just iterate
                # But we need to filter for capabillity "can_do"
                
                # Simplified loop: Find best candidate in list
                chosen = None
                for candidate in remaining:
                    if can_do(str(candidate["_id"]), "CADE 30"):
                        chosen = candidate
                        break
                
                if not chosen:
                    self.log(f"   [Debug] No valid candidate found for CADE 30 among {len(remaining)} remaining.")
                    break
                
                self._add_event(chosen, day_str, "CADE 30")
                uid = str(chosen["_id"])
                assigned_today.add(uid)
                current_assignments[uid] = "CADE 30"
                remaining.remove(chosen)
                cade30_count[uid] += 1
                filled_30 += 1

            if filled_30 < self.REQ_CADE_30:
                msg = f"Faltan {self.REQ_CADE_30 - filled_30} personas para CADE 30 el {day_str}. (Cubiertos: {filled_30})"
                self.log(f"CRITICAL WARNING: {msg}")
                self.warnings.append({"date": day_str, "type": "CADE 30", "message": msg, "severity": "critical"})

            # --- CADE 50 ---
            db_50_count = sum(1 for e_type in self.existing_events.get(day_str, {}).values() if e_type == "CADE 50")
            gen_50_count = sum(1 for e in self.generated_events if e["fecha_inicio"] == day_str and e["tipo"] == "CADE 50")
            filled_50 = db_50_count + gen_50_count
            
            needed_50 = self.REQ_CADE_50 - filled_50
            self.log(f"   [Debug] CADE 50 Needed: {needed_50}. Pool size: {len(remaining)}")

            remaining.sort(key=lambda u: pick_candidate_key(u, "CADE 50"))

            while filled_50 < self.REQ_CADE_50 and remaining:
                chosen = None
                for candidate in remaining:
                    if can_do(str(candidate["_id"]), "CADE 50"):
                        chosen = candidate
                        break

                if not chosen:
                    self.log(f"   [Debug] No valid candidate found for CADE 50 among {len(remaining)} remaining.")
                    break  
                self._add_event(chosen, day_str, "CADE 50")
                uid = str(chosen["_id"])
                assigned_today.add(uid)
                current_assignments[uid] = "CADE 50"
                remaining.remove(chosen)
                cade50_count[uid] += 1
                filled_50 += 1
            
            if filled_50 < self.REQ_CADE_50:
                msg = f"Faltan {self.REQ_CADE_50 - filled_50} personas para CADE 50 el {day_str}. (Cubiertos: {filled_50})"
                self.log(f"CRITICAL WARNING: {msg}")
                self.warnings.append({"date": day_str, "type": "CADE 50", "message": msg, "severity": "critical"})

            # --- MAIL (Tag or Role Based) ---
            db_mail_count = sum(1 for e_type in self.existing_events.get(day_str, {}).values() if e_type == "Mail")
            gen_mail_count = sum(1 for e in self.generated_events if e["fecha_inicio"] == day_str and e["tipo"] == "Mail")
            filled_mail = db_mail_count + gen_mail_count
            
            needed_mail = self.REQ_MAIL - filled_mail
            self.log(f"   [Debug] Mail Needed: {needed_mail}. Pool size: {len(remaining)}")
            
            while filled_mail < self.REQ_MAIL:
                # Find candidates from REMAINING pool who have "Mail" skill or Role
                mail_candidates = [u for u in remaining if has_mail_skill(u)]
                
                if not mail_candidates:
                    self.log(f"   [Debug] No Mail candidates found among {len(remaining)} remaining users.")
                    break
                    
                # Sort: Sticky > Shuffled
                mail_candidates.sort(key=lambda u: (
                    0 if str(u["_id"]) in self.last_assignments and self.last_assignments[str(u["_id"])] == "Mail" else 1,
                    1 if str(u["_id"]) in self.last_week_roles and self.last_week_roles[str(u["_id"])] == "Mail" else 0
                ))
                
                chosen = mail_candidates[0]
                self._add_event(chosen, day_str, "Mail")
                uid = str(chosen["_id"])
                assigned_today.add(uid)
                current_assignments[uid] = "Mail"
                remaining.remove(chosen)
                filled_mail += 1

            if filled_mail < self.REQ_MAIL:
                msg = f"Faltan {self.REQ_MAIL - filled_mail} personas para MAIL el {day_str}. (Cubiertos: {filled_mail})"
                self.log(f"WARNING: {msg}")
                self.warnings.append({"date": day_str, "type": "Mail", "message": msg, "severity": "warning"})

            # --- RESTO (PIAS) ---
            # REMOVED EXPLICIT PIAS GENERATION
            # Users remaining without assignment are implicitly "Available/PIAS"
            # and will show as blank/default in the calendar.
            
            # UPDATE LAST ASSIGNMENTS FOR NEXT DAY
            self.last_assignments = current_assignments


        return self.generated_events

    def _add_event(self, user, date_str, tipo):
        full_name = f"{user.get('nombre', '')} {user.get('apellidos', '')}".strip()
        self.generated_events.append({
            "trabajador": full_name,
            "fecha_inicio": date_str,
            "fecha_fin": date_str,
            "tipo": tipo
        })
        
        # Track role for weekly history
        if "id" in user:
             uid = str(user["id"])
        elif "_id" in user:
             uid = str(user["_id"])
        else:
             uid = user.get("usuario") # Fallback
             
        if uid:
             self.current_week_roles[uid] = tipo

    def save_results(self):
        """Persiste los resultados a Mongo."""
        if not self.generated_events:
            return
            
        self.log(f"Saving {len(self.generated_events)} events to DB...")
        # TODO: Borrar eventos generados previos si se re-ejecuta? 
        # Por seguridad, el flujo debería ser: Preview en UI -> Confirmar -> Save.
        # Aquí solo implemento la inserción.
        if events_collection is not None:
            events_collection.insert_many(self.generated_events)
            self.log("Saved successfully.")

# Bloque de prueba standalone
if __name__ == "__main__":
    generator = ShiftGenerator()
    generator.fetch_data()
    # Mock date
    next_month = date.today().replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    
    generator.load_existing_events(next_month.year, next_month.month)
    results = generator.generate(next_month.year, next_month.month)
    
    print("\n--- RESUMEN DE GENERACIÓN ---")
    print(f"Total Eventos Generados: {len(results)}")
    print("Muestra (primeros 5):")
    for r in results[:5]:
        print(r)
