#!/usr/bin/env python3
"""
🎛️ Interactive Calibration Manager

כלי אינטראקטיבי לניהול וכיול המערכת בזמן אמת
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import argparse

class CalibrationManager:
    """מנהל כיול אינטראקטיבי"""
    
    def __init__(self, config_path: str = "config/calibration_settings.json"):
        self.config_path = config_path
        self.settings = self._load_settings()
        
    def _load_settings(self) -> Dict[str, Any]:
        """טעינת הגדרות כיול"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # הגדרות ברירת מחדל
        return {
            "ml_threshold": 0.50,
            "score_weights": {
                "w_prob": 0.55,
                "w_rr": 0.25,
                "w_fresh": 0.15,
                "w_pattern": 0.05
            },
            "auto_calibration": {
                "enabled": True,
                "min_samples": 20,
                "max_threshold_change": 0.10,
                "review_frequency_days": 7
            },
            "performance_thresholds": {
                "poor_performance": 0.45,
                "good_performance": 0.70,
                "excellent_performance": 0.80
            },
            "calibration_history": []
        }
    
    def _save_settings(self):
        """שמירת הגדרות"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
    
    def get_current_config(self) -> Dict[str, Any]:
        """קבלת התצורה הנוכחית"""
        return {
            "ml_threshold": self.settings["ml_threshold"],
            "weights": self.settings["score_weights"].copy(),
            "last_calibration": self.settings["calibration_history"][-1] if self.settings["calibration_history"] else None
        }
    
    def apply_calibration(self, adjustments: Dict[str, Any], reason: str = "", auto: bool = False) -> bool:
        """יישום כיול חדש"""
        try:
            old_config = self.get_current_config()
            
            # עדכון סף ML
            if "ml_threshold" in adjustments:
                new_threshold = adjustments["ml_threshold"]
                max_change = self.settings["auto_calibration"]["max_threshold_change"]
                
                # בדיקת גבולות בטיחות
                if abs(new_threshold - self.settings["ml_threshold"]) > max_change and auto:
                    print(f"❌ שינוי סף גדול מדי ({new_threshold - self.settings['ml_threshold']:+.3f}) - דורש אישור ידני")
                    return False
                
                if not 0.2 <= new_threshold <= 0.9:
                    print(f"❌ סף לא תקין: {new_threshold} (חייב להיות בין 0.2-0.9)")
                    return False
                
                self.settings["ml_threshold"] = new_threshold
            
            # עדכון משקלים
            if "weights" in adjustments:
                new_weights = adjustments["weights"]
                
                # בדיקת תקינות משקלים
                total_weight = sum(new_weights.values())
                if abs(total_weight - 1.0) > 0.01:
                    print(f"❌ סכום משקלים לא תקין: {total_weight} (חייב להיות 1.0)")
                    return False
                
                self.settings["score_weights"].update(new_weights)
            
            # תיעוד השינוי
            calibration_record = {
                "timestamp": datetime.now().isoformat(),
                "old_config": old_config,
                "new_config": self.get_current_config(),
                "adjustments": adjustments,
                "reason": reason,
                "auto_applied": auto
            }
            
            self.settings["calibration_history"].append(calibration_record)
            
            # שמירה
            self._save_settings()
            
            print(f"✅ כיול יושם בהצלחה ({'אוטומטי' if auto else 'ידני'})")
            self._print_changes_summary(old_config, self.get_current_config())
            
            return True
            
        except Exception as e:
            print(f"❌ שגיאה ביישום הכיול: {e}")
            return False
    
    def _print_changes_summary(self, old_config: Dict, new_config: Dict):
        """הדפסת סיכום השינויים"""
        print("\n📊 סיכום השינויים:")
        print("-" * 30)
        
        # שינוי סף
        if old_config["ml_threshold"] != new_config["ml_threshold"]:
            change = new_config["ml_threshold"] - old_config["ml_threshold"]
            print(f"🎯 ML Threshold: {old_config['ml_threshold']:.3f} → {new_config['ml_threshold']:.3f} ({change:+.3f})")
        
        # שינוי משקלים
        old_weights = old_config["weights"]
        new_weights = new_config["weights"]
        
        for weight_name in old_weights:
            if abs(old_weights[weight_name] - new_weights[weight_name]) > 0.01:
                change = new_weights[weight_name] - old_weights[weight_name]
                print(f"⚖️  {weight_name}: {old_weights[weight_name]:.2f} → {new_weights[weight_name]:.2f} ({change:+.2f})")
        print()
    
    def get_calibration_history(self, limit: int = 10) -> List[Dict]:
        """קבלת היסטוריית כיולים"""
        return self.settings["calibration_history"][-limit:]
    
    def rollback_calibration(self) -> bool:
        """חזרה לכיול קודם"""
        if not self.settings["calibration_history"]:
            print("❌ אין כיולים קודמים לחזרה")
            return False
        
        try:
            last_calibration = self.settings["calibration_history"][-1]
            old_config = last_calibration["old_config"]
            
            # שחזור הגדרות
            self.settings["ml_threshold"] = old_config["ml_threshold"]
            self.settings["score_weights"] = old_config["weights"]
            
            # הסרת הכיול האחרון מההיסטוריה
            self.settings["calibration_history"].pop()
            
            # תיעוד החזרה
            rollback_record = {
                "timestamp": datetime.now().isoformat(),
                "action": "rollback",
                "reverted_to": old_config
            }
            self.settings["calibration_history"].append(rollback_record)
            
            self._save_settings()
            print("✅ חזרה לכיול קודם בוצעה בהצלחה")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בחזרה לכיול קודם: {e}")
            return False
    
    def interactive_calibration_wizard(self):
        """אשף כיול אינטראקטיבי"""
        print("🧙‍♂️ אשף כיול המערכת")
        print("=" * 40)
        
        current = self.get_current_config()
        
        print(f"\n📊 התצורה הנוכחית:")
        print(f"🎯 ML Threshold: {current['ml_threshold']:.3f}")
        print(f"⚖️  משקלי ציון:")
        for name, value in current['weights'].items():
            print(f"   {name}: {value:.2f}")
        
        print(f"\n🔄 מה תרצה לעשות?")
        print("1. שינוי סף ML")
        print("2. התאמת משקלים")
        print("3. כיול אוטומטי מומלץ")
        print("4. צפייה בהיסטוריית כיולים")
        print("5. חזרה לכיול קודם")
        print("0. יציאה")
        
        try:
            choice = input("\n👉 בחירה: ").strip()
            
            if choice == "1":
                self._adjust_ml_threshold_interactive()
            elif choice == "2":
                self._adjust_weights_interactive()
            elif choice == "3":
                self._auto_calibration_interactive()
            elif choice == "4":
                self._show_history()
            elif choice == "5":
                self.rollback_calibration()
            elif choice == "0":
                print("👋 יציאה מהאשף")
                return
            else:
                print("❌ בחירה לא תקינה")
                
        except KeyboardInterrupt:
            print("\n👋 יציאה מהאשף")
    
    def _adjust_ml_threshold_interactive(self):
        """שינוי סף ML אינטראקטיבי"""
        current_threshold = self.settings["ml_threshold"]
        
        print(f"\n🎯 סף ML נוכחי: {current_threshold:.3f}")
        print("📖 מדריך:")
        print("   • 0.3-0.4: אגרסיבי (יותר תוצאות, פחות מדויק)")
        print("   • 0.5-0.6: מאוזן")
        print("   • 0.7-0.8: שמרני (פחות תוצאות, יותר מדויק)")
        
        try:
            new_threshold = float(input(f"👉 סף חדש (0.2-0.9): ").strip())
            
            if 0.2 <= new_threshold <= 0.9:
                reason = input("📝 סיבה לשינוי (אופציונלי): ").strip()
                
                adjustments = {"ml_threshold": new_threshold}
                if self.apply_calibration(adjustments, reason or "שינוי ידני של סף ML"):
                    print("✅ סף ML עודכן בהצלחה!")
            else:
                print("❌ סף לא תקין - חייב להיות בין 0.2 ל-0.9")
                
        except ValueError:
            print("❌ נא להזין מספר תקין")
    
    def _adjust_weights_interactive(self):
        """התאמת משקלים אינטראקטיבי"""
        current_weights = self.settings["score_weights"].copy()
        
        print(f"\n⚖️ משקלים נוכחיים:")
        for name, value in current_weights.items():
            print(f"   {name}: {value:.2f}")
        
        print("\n📖 מדריך למשקלים:")
        print("   • w_prob: משקל ל-ML prediction (בדרך כלל 0.4-0.7)")
        print("   • w_rr: משקל ל-Risk/Reward (בדרך כלל 0.2-0.4)")
        print("   • w_fresh: משקל לטריות האות (בדרך כלל 0.1-0.2)")
        print("   • w_pattern: משקל לדפוסים טכניים (בדרך כלל 0.05-0.15)")
        
        new_weights = {}
        total_so_far = 0.0
        
        for name, current_value in current_weights.items():
            try:
                remaining = 1.0 - total_so_far
                prompt = f"👉 {name} (נוכחי: {current_value:.2f}, נותר: {remaining:.2f}): "
                
                user_input = input(prompt).strip()
                if user_input:  # אם המשתמש הזין ערך
                    new_value = float(user_input)
                    if 0 <= new_value <= remaining:
                        new_weights[name] = new_value
                        total_so_far += new_value
                    else:
                        print(f"❌ ערך לא תקין - חייב להיות בין 0 ל-{remaining:.2f}")
                        return
                else:  # אם המשתמש לא הזין ערך - השאר את הנוכחי
                    new_weights[name] = current_value
                    total_so_far += current_value
                    
            except ValueError:
                print("❌ נא להזין מספר תקין")
                return
        
        # נרמול לוודא שהסכום הוא 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v/total for k, v in new_weights.items()}
            
            reason = input("📝 סיבה לשינוי (אופציונלי): ").strip()
            
            adjustments = {"weights": new_weights}
            if self.apply_calibration(adjustments, reason or "שינוי ידני של משקלים"):
                print("✅ משקלים עודכנו בהצלחה!")
        else:
            print("❌ שגיאה בחישוב המשקלים")
    
    def _auto_calibration_interactive(self):
        """כיול אוטומטי אינטראקטיבי"""
        print("\n🤖 כיול אוטומטי")
        print("=" * 20)
        print("⚠️  תכונה זו דורשת נתוני ביצועים עדכניים")
        print("📊 בסביבת ייצור, כאן יתבצע ניתוח הביצועים האמיתי")
        
        # דמיונות ביצועים (בפועל יבוא מה-evaluation.py)
        mock_performance = {
            'accuracy_5d': 0.58,  # ביצועים בינוניים-נמוכים
            'total_predictions': 25,
            'high_conf_accuracy': 0.65
        }
        
        print(f"\n📈 ביצועים נוכחיים (מדומה):")
        print(f"   • דיוק 5 ימים: {mock_performance['accuracy_5d']:.1%}")
        print(f"   • תחזיות בסך הכל: {mock_performance['total_predictions']}")
        print(f"   • דיוק ביטחון גבוה: {mock_performance['high_conf_accuracy']:.1%}")
        
        # כיול מוצע
        if mock_performance['accuracy_5d'] < 0.6:
            suggested_adjustments = {
                "ml_threshold": min(0.8, self.settings["ml_threshold"] + 0.05),
                "weights": {
                    "w_prob": 0.50,  # פחות משקל ל-ML
                    "w_rr": 0.30,    # יותר למדדים טכניים
                    "w_fresh": 0.15,
                    "w_pattern": 0.05
                }
            }
            
            print(f"\n🎯 כיול מוצע:")
            print(f"   • העלה סף ML ל-{suggested_adjustments['ml_threshold']:.3f}")
            print(f"   • הפחת משקל ML ל-{suggested_adjustments['weights']['w_prob']:.2f}")
            print(f"   • הגדל משקל R/R ל-{suggested_adjustments['weights']['w_rr']:.2f}")
            
            confirm = input(f"\n👉 להחיל כיול זה? (y/n): ").strip().lower()
            if confirm == 'y':
                reason = "כיול אוטומטי - ביצועים נמוכים"
                if self.apply_calibration(suggested_adjustments, reason, auto=True):
                    print("✅ כיול אוטומטי הוחל בהצלחה!")
            else:
                print("❌ כיול אוטומטי בוטל")
        else:
            print("\n✅ הביצועים טובים - אין צורך בכיול כרגע")
    
    def _show_history(self):
        """הצגת היסטוריית כיולים"""
        history = self.get_calibration_history()
        
        if not history:
            print("\n📋 אין היסטוריית כיולים")
            return
        
        print(f"\n📋 היסטוריית כיולים ({len(history)} אחרונים):")
        print("=" * 50)
        
        for i, record in enumerate(reversed(history), 1):
            timestamp = record.get('timestamp', 'N/A')
            reason = record.get('reason', 'לא צוין')
            auto = record.get('auto_applied', False)
            
            print(f"\n{i}. {timestamp}")
            print(f"   📝 סיבה: {reason}")
            print(f"   🤖 אוטומטי: {'כן' if auto else 'לא'}")
            
            if 'adjustments' in record:
                adj = record['adjustments']
                if 'ml_threshold' in adj:
                    old_th = record.get('old_config', {}).get('ml_threshold', 'N/A')
                    print(f"   🎯 סף ML: {old_th} → {adj['ml_threshold']}")

def main():
    """פונקציית ראשית"""
    parser = argparse.ArgumentParser(description='מנהל כיול דינמי למערכת ML')
    parser.add_argument('--config', default='config/calibration_settings.json', 
                       help='נתיב לקובץ הגדרות')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='מצב אינטראקטיבי')
    
    args = parser.parse_args()
    
    manager = CalibrationManager(args.config)
    
    if args.interactive:
        try:
            while True:
                manager.interactive_calibration_wizard()
                
                continue_choice = input("\n🔄 להמשיך לפעולה נוספת? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    break
        except KeyboardInterrupt:
            print("\n👋 יציאה")
    else:
        # מצב לא אינטראקטיבי - הצגת סטטוס
        current = manager.get_current_config()
        print("📊 התצורה הנוכחית:")
        print(f"🎯 ML Threshold: {current['ml_threshold']:.3f}")
        print("⚖️  משקלי ציון:")
        for name, value in current['weights'].items():
            print(f"   {name}: {value:.2f}")
        
        history = manager.get_calibration_history(3)
        if history:
            print(f"\n📋 כיולים אחרונים: {len(history)}")
            for record in history[-3:]:
                timestamp = record.get('timestamp', 'N/A')[:16]  # חתוך תאריך
                reason = record.get('reason', 'לא צוין')[:30]   # חתוך סיבה
                print(f"   • {timestamp}: {reason}")

if __name__ == "__main__":
    main()