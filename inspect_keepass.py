#!/usr/bin/env python3
"""KeePass Database Inspector

Dieses Skript liest die KeePass-Datei aus und zeigt die Ordnerstruktur
sowie alle Einträge an, um das Layout zu verstehen.
"""

import sys
from pathlib import Path
from pykeepass import PyKeePass

def print_group_structure(group, level=0):
    """Rekursiv die Gruppenstruktur ausgeben."""
    indent = "  " * level
    print(f"{indent}📁 {group.name}")
    
    # Einträge in dieser Gruppe
    for entry in group.entries:
        print(f"{indent}  📄 {entry.title}")
        if entry.username:
            print(f"{indent}    👤 Username: {entry.username}")
        if entry.url:
            print(f"{indent}    🌐 URL: {entry.url}")
        if entry.notes:
            print(f"{indent}    📝 Notes: {entry.notes[:50]}...")
        if entry.attachments:
            print(f"{indent}    📎 Attachments: {[att.filename for att in entry.attachments]}")
    
    # Untergruppen
    for subgroup in group.subgroups:
        print_group_structure(subgroup, level + 1)

def inspect_keepass_database(database_path, password):
    """Inspect the KeePass database structure."""
    try:
        print(f"🔍 Inspiziere KeePass-Datenbank: {database_path}")
        print("=" * 60)
        
        kp = PyKeePass(database_path, password=password)
        
        print(f"📊 Datenbank-Info:")
        print(f"   Root-Gruppe: {kp.root_group.name}")
        print()
        
        print("📂 Ordnerstruktur:")
        print_group_structure(kp.root_group)
        
        print()
        print("🔍 Suche nach spezifischen Einträgen:")
        
        # Suche nach SSH-Einträgen
        ssh_entries = kp.find_entries(title="SSH")
        print(f"   SSH-Einträge gefunden: {len(ssh_entries)}")
        for entry in ssh_entries:
            print(f"     - {entry.title} (in Gruppe: {entry.group.name})")
            if entry.attachments:
                print(f"       Anhänge: {[att.filename for att in entry.attachments]}")
        
        # Suche nach MySQL-Einträgen
        mysql_entries = kp.find_entries(title="MySQL")
        print(f"   MySQL-Einträge gefunden: {len(mysql_entries)}")
        for entry in mysql_entries:
            print(f"     - {entry.title} (in Gruppe: {entry.group.name})")
        
        # Suche nach "Datenbank"-Gruppe
        db_group = kp.find_groups(name="Datenbank", first=True)
        if db_group:
            print(f"   📁 'Datenbank'-Gruppe gefunden:")
            print_group_structure(db_group, 1)
        else:
            print("   ❌ 'Datenbank'-Gruppe nicht gefunden")
        
        # Suche nach allen Gruppen mit "Datenbank" im Namen
        all_db_groups = kp.find_groups(name="Datenbank")
        print(f"   📁 Alle Gruppen mit 'Datenbank' im Namen: {len(all_db_groups)}")
        for group in all_db_groups:
            print(f"     - {group.name} (Pfad: {group.path})")
        
        # Zeige alle Gruppen an
        print()
        print("📂 Alle verfügbaren Gruppen:")
        def list_all_groups(group, level=0):
            indent = "  " * level
            print(f"{indent}📁 {group.name}")
            for subgroup in group.subgroups:
                list_all_groups(subgroup, level + 1)
        
        list_all_groups(kp.root_group)
        
    except Exception as e:
        print(f"❌ Fehler beim Lesen der KeePass-Datei: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Pfad zur KeePass-Datei
    credentials_path = Path("credentials.kdbx")
    
    if not credentials_path.exists():
        print(f"❌ KeePass-Datei nicht gefunden: {credentials_path}")
        sys.exit(1)
    
    # Passwort abfragen
    password = input("🔐 KeePass Master-Passwort eingeben: ")
    
    # Datenbank inspizieren
    success = inspect_keepass_database(credentials_path, password)
    
    if success:
        print("\n✅ KeePass-Datenbank erfolgreich inspiziert!")
    else:
        print("\n❌ Fehler beim Inspizieren der KeePass-Datenbank!")
        sys.exit(1) 