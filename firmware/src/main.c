/*
 * JRWatch — main state machine.
 *
 * The whole application is event-driven: between events the SoC sits in
 * System ON idle (WFI via the Zephyr idle thread) and every peripheral is
 * either gated (display/IMU load switches) or in its lowest device state.
 * The measured/projected budget per state lives in docs/verification-report.md.
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/input/input.h>

#include "jrwatch.h"

LOG_MODULE_REGISTER(main, CONFIG_LOG_DEFAULT_LEVEL);

struct jr_status jr_status;
K_EVENT_DEFINE(jr_events);

/* after this long with no motion/button/BLE activity, drop to IDLE */
#define ACTIVE_TIMEOUT   K_SECONDS(20)
/* battery/status refresh cadence while active */
#define ACTIVE_TICK      K_SECONDS(5)
/* very long press of the user button requests ship mode */
#define SHIP_HOLD_MS     5000

static int64_t last_button_down;

static void button_cb(struct input_event *evt, void *user_data)
{
	ARG_UNUSED(user_data);

	if (evt->code != INPUT_KEY_0) {
		return;
	}
	if (evt->value) {
		last_button_down = k_uptime_get();
	} else {
		if (k_uptime_get() - last_button_down >= SHIP_HOLD_MS) {
			LOG_INF("long press -> ship mode");
			jr_power_ship_mode();   /* does not return */
		}
	}
	k_event_post(&jr_events, JR_EVT_BUTTON);
}
INPUT_CALLBACK_DEFINE(NULL, button_cb, NULL);

static void enter_active(void)
{
	jr_status.state = JR_STATE_ACTIVE;
	jr_power_imu_rail(true);
	jr_motion_active();
	jr_ui_display_power(true);
	jr_power_sample();
	jr_ui_render();
	LOG_INF("state: ACTIVE");
}

static void enter_idle(void)
{
	jr_status.state = JR_STATE_IDLE;
	/* display keeps its last frame at ~µW: MIP retains the image and the
	 * EXTCOMIN 1 Hz toggle is driven by the display driver from a timer.
	 * The IMU drops to its 25 Hz low-power any-motion mode (~6 µA). */
	jr_motion_arm_wake();
	jr_ui_render();          /* final face refresh before going quiet */
	LOG_INF("state: IDLE (armed sleep)");
}

int main(void)
{
	int64_t last_activity = k_uptime_get();

	LOG_INF("JRWatch r1 firmware boot");

	(void)jr_power_init();
	(void)jr_ui_init();
	(void)jr_motion_init();
	(void)jr_ble_init();

	enter_active();

	while (1) {
		uint32_t ev = k_event_wait(&jr_events,
					   JR_EVT_MOTION | JR_EVT_BUTTON | JR_EVT_TICK,
					   false, ACTIVE_TICK);
		k_event_clear(&jr_events, ev);

		if (ev & (JR_EVT_MOTION | JR_EVT_BUTTON)) {
			last_activity = k_uptime_get();
			if (jr_status.state == JR_STATE_IDLE) {
				enter_active();
			}
		}

		if (jr_status.state == JR_STATE_ACTIVE) {
			jr_motion_poll_steps();
			jr_power_sample();
			jr_ui_render();
			jr_ble_notify_steps(jr_status.steps);

			if (k_uptime_get() - last_activity >
			    k_ticks_to_ms_floor64(ACTIVE_TIMEOUT.ticks)) {
				enter_idle();
			}
		}
	}
	return 0;
}
