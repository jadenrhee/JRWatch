/* JRWatch firmware — shared state and module interfaces. */
#ifndef JRWATCH_H_
#define JRWATCH_H_

#include <zephyr/kernel.h>

/* Power tiers (documented in docs/verification-report.md):
 *  ACTIVE    — display on, BLE connectable, IMU 50 Hz
 *  IDLE      — "armed sleep": System ON idle, IMU any-motion wake armed,
 *              display holding a static face, BLE off or slow advertising
 *  (ship mode is entered via the PMIC and exits only by SW1/VBUS)
 */
enum jr_state {
	JR_STATE_ACTIVE,
	JR_STATE_IDLE,
};

struct jr_status {
	uint8_t battery_pct;
	int32_t vbat_mv;
	bool charging;
	uint32_t steps;
	enum jr_state state;
};

extern struct jr_status jr_status;

/* Raised by motion (IMU any-motion) and the user button; consumed by main. */
extern struct k_event jr_events;
#define JR_EVT_MOTION   BIT(0)
#define JR_EVT_BUTTON   BIT(1)
#define JR_EVT_TICK     BIT(2)

int jr_ble_init(void);
void jr_ble_notify_steps(uint32_t steps);

int jr_motion_init(void);
int jr_motion_arm_wake(void);      /* low-power any-motion mode */
int jr_motion_active(void);        /* 50 Hz sampling for step counting */
void jr_motion_poll_steps(void);

int jr_ui_init(void);
void jr_ui_render(void);           /* redraws only when content changed */
int jr_ui_display_power(bool on);  /* gates the VDD_DISP load switch */

int jr_power_init(void);
void jr_power_sample(void);        /* refresh vbat/soc/charging */
void jr_power_imu_rail(bool on);   /* gates the VDD_IMU load switch */
void jr_power_ship_mode(void);     /* PMIC ship mode: ~sub-µA, SW1 wakes */

#endif /* JRWATCH_H_ */
