# database.py - Database operations for custom pallets
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH, DB_CONFIG, logger

class DatabaseManager:
    """Manages database operations for custom pallets"""
    
    def __init__(self, db_path=None):
        self.db_path = str(db_path) if db_path else str(DB_PATH)
        self.logger = logger
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path, timeout=DB_CONFIG['timeout']) as conn:
                cur = conn.cursor()
                
                # Custom pallets table
                cur.execute(f'''
                    CREATE TABLE IF NOT EXISTS {DB_CONFIG['custom_pallet_table']} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pallet_id TEXT UNIQUE NOT NULL,
                        customer_name TEXT,
                        total_kegs INTEGER DEFAULT 0,
                        source_locations TEXT,  -- JSON array of locations
                        keg_data TEXT,          -- JSON array of keg entries
                        beer_type TEXT DEFAULT 'Mixed',
                        batch TEXT,
                        filling_date TEXT,
                        status TEXT DEFAULT 'assembling',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        qr_generated INTEGER DEFAULT 0,
                        qr_data TEXT,
                        allocated_to TEXT,
                        allocated_at DATETIME,
                        operator TEXT,
                        notes TEXT
                    )
                ''')
                
                # Custom keg locations table
                cur.execute(f'''
                    CREATE TABLE IF NOT EXISTS {DB_CONFIG['custom_keg_table']} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        custom_pallet_id TEXT NOT NULL,
                        source_location TEXT NOT NULL,
                        keg_count INTEGER NOT NULL,
                        keg_qrs TEXT,  -- JSON array of QR codes
                        taken_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        operator TEXT,
                        FOREIGN KEY (custom_pallet_id) REFERENCES {DB_CONFIG['custom_pallet_table']}(pallet_id)
                    )
                ''')
                
                # Create indexes
                cur.execute(f'''
                    CREATE INDEX IF NOT EXISTS idx_custom_pallet_status 
                    ON {DB_CONFIG['custom_pallet_table']}(status)
                ''')
                
                cur.execute(f'''
                    CREATE INDEX IF NOT EXISTS idx_custom_pallet_customer 
                    ON {DB_CONFIG['custom_pallet_table']}(customer_name)
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_custom_pallet(self, pallet_data: Dict[str, Any]) -> bool:
        """Create a new custom pallet record"""
        try:
            with sqlite3.connect(self.db_path, timeout=DB_CONFIG['timeout']) as conn:
                cur = conn.cursor()
                
                # Convert lists to JSON strings
                source_locations = json.dumps(pallet_data.get('source_locations', []))
                keg_data = json.dumps(pallet_data.get('keg_data', []))
                
                cur.execute(f'''
                    INSERT INTO {DB_CONFIG['custom_pallet_table']} 
                    (pallet_id, customer_name, total_kegs, source_locations, keg_data,
                     beer_type, batch, filling_date, status, operator, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pallet_data.get('pallet_id'),
                    pallet_data.get('customer_name'),
                    pallet_data.get('total_kegs', 0),
                    source_locations,
                    keg_data,
                    pallet_data.get('beer_type', 'Mixed'),
                    pallet_data.get('batch'),
                    pallet_data.get('filling_date'),
                    pallet_data.get('status', 'assembling'),
                    pallet_data.get('operator', 'Operator'),
                    pallet_data.get('notes', '')
                ))
                
                conn.commit()
                self.logger.info(f"Created pallet record: {pallet_data.get('pallet_id')}")
                return True
        
        except sqlite3.IntegrityError:
            self.logger.warning(f"Pallet already exists: {pallet_data.get('pallet_id')}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to create pallet record: {e}")
            return False
    
    def add_keg_entry(self, pallet_id: str, location: str, count: int, qr_codes: List[str] = None) -> bool:
        """Add keg entry to database"""
        try:
            with sqlite3.connect(self.db_path, timeout=DB_CONFIG['timeout']) as conn:
                cur = conn.cursor()
                
                keg_qrs = json.dumps(qr_codes or [])
                
                cur.execute(f'''
                    INSERT INTO {DB_CONFIG['custom_keg_table']} 
                    (custom_pallet_id, source_location, keg_count, keg_qrs, operator)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pallet_id, location, count, keg_qrs, 'Operator'))
                
                conn.commit()
                self.logger.info(f"Added keg entry: {count} kegs from {location} to {pallet_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Failed to add keg entry: {e}")
            return False
    
    def update_pallet_status(self, pallet_id: str, status: str, **kwargs) -> bool:
        """Update pallet status and other fields"""
        try:
            with sqlite3.connect(self.db_path, timeout=DB_CONFIG['timeout']) as conn:
                cur = conn.cursor()
                
                # Build update query dynamically
                updates = ["status = ?"]
                params = [status]
                
                if 'customer_name' in kwargs:
                    updates.append("customer_name = ?")
                    params.append(kwargs['customer_name'])
                
                if 'allocated_to' in kwargs:
                    updates.append("allocated_to = ?")
                    updates.append("allocated_at = DATETIME('now')")
                    params.append(kwargs['allocated_to'])
                
                if 'qr_data' in kwargs:
                    updates.append("qr_generated = 1")
                    updates.append("qr_data = ?")
                    params.append(kwargs['qr_data'])
                
                updates_str = ", ".join(updates)
                params.append(pallet_id)
                
                cur.execute(f'''
                    UPDATE {DB_CONFIG['custom_pallet_table']}
                    SET {updates_str}
                    WHERE pallet_id = ?
                ''', params)
                
                conn.commit()
                self.logger.info(f"Updated pallet {pallet_id} status to {status}")
                return True
        
        except Exception as e:
            self.logger.error(f"Failed to update pallet status: {e}")
            return False
    
    def get_pallet(self, pallet_id: str) -> Optional[Dict[str, Any]]:
        """Get pallet by ID"""
        try:
            with sqlite3.connect(self.db_path, timeout=DB_CONFIG['timeout']) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                
                cur.execute(f'''
                    SELECT * FROM {DB_CONFIG['custom_pallet_table']}
                    WHERE pallet_id = ?
                ''', (pallet_id,))
                
                row = cur.fetchone()
                if row:
                    # Convert row to dict and parse JSON fields
                    pallet = dict(row)
                    pallet['source_locations'] = json.loads(pallet['source_locations'] or '[]')
                    pallet['keg_data'] = json.loads(pallet['keg_data'] or '[]')
                    return pallet
                return None
        
        except Exception as e:
            self.logger.error(f"Failed to get pallet: {e}")
            return None
    
    def get_recent_pallets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent custom pallets"""
        try:
            with sqlite3.connect(self.db_path, timeout=DB_CONFIG['timeout']) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                
                cur.execute(f'''
                    SELECT pallet_id, total_kegs, status, customer_name,
                           created_at, filling_date, batch
                    FROM {DB_CONFIG['custom_pallet_table']}
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        
        except Exception as e:
            self.logger.error(f"Failed to get recent pallets: {e}")
            return []
    
    def get_keg_entries(self, pallet_id: str) -> List[Dict[str, Any]]:
        """Get all keg entries for a pallet"""
        try:
            with sqlite3.connect(self.db_path, timeout=DB_CONFIG['timeout']) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                
                cur.execute(f'''
                    SELECT * FROM {DB_CONFIG['custom_keg_table']}
                    WHERE custom_pallet_id = ?
                    ORDER BY taken_at DESC
                ''', (pallet_id,))
                
                rows = cur.fetchall()
                result = []
                for row in rows:
                    entry = dict(row)
                    entry['keg_qrs'] = json.loads(entry['keg_qrs'] or '[]')
                    result.append(entry)
                return result
        
        except Exception as e:
            self.logger.error(f"Failed to get keg entries: {e}")
            return []

# Singleton instance
_db_instance = None

def get_database():
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance