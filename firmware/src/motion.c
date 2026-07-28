/*
 * BMI270: motion wake + host-side step estimation.
 *
 * Power design: in IDLE the IMU runs its low-power accel mode with the
 * any-motion interrupt armed (INT1 -> P0.25) at ~6 µA and the SoC sleeps.
 * In ACTIVE a 20 ms work item samples at the accel's 50 Hz ODR and runs a
 * lightweight peak-detector for steps; the work is cancelled on the drop
 * to IDLE. The BMI270's hardware step counter is not exposed by the Zephyr
 * driver; moving counting on-chip is a documented follow-up that will cut
 * ACTIVE-state SoC wakeups further (see firmware/README.md).
 *
 * Init order: VDD_IMU is a boot-off load switch, so the chip is dark while
 * Zephyr's POST_KERNEL init runs. The devicetree node is zephyr,deferred-init
 * and jr_motion_init() (called by main() after the rail is up) runs the
 * driver's init by hand.
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>

#include "jrwatch.h"

LOG_MODULE_REGISTER(motion, CONFIG_LOG_DEFAULT_LEVEL);

static const struct device *const imu = DEVICE_DT_GET_ONE(bosch_bmi270);

/* ACTIVE-state step sampling cadence — matches the 50 Hz accel ODR */
#define STEP_SAMPLE_MS   20

static void motion_trigger(const struct device *dev,
			   const struct sensor_trigger *trig)
{
	ARG_UNUSED(dev);
	ARG_UNUSED(trig);
	k_event_post(&jr_events, JR_EVT_MOTION);
}

static int set_accel(uint16_t hz, const char *why)
{
	struct sensor_value odr = { .val1 = hz, .val2 = 0 };
	int err = sensor_attr_set(imu, SENSOR_CHAN_ACCEL_XYZ,
				  SENSOR_ATTR_SAMPLING_FREQUENCY, &odr);

	if (err) {
		LOG_WRN("accel odr %u (%s): %d", hz, why, err);
	}
	return err;
}

int jr_motion_init(void)
{
	if (!device_is_ready(imu)) {
		/* deferred init (see dts): the rail is up now, probe the chip */
		int err = device_init(imu);

		if (err) {
			LOG_ERR("BMI270 init: %d", err);
			return err;
		}
	}

	/* +/-4g range */
	struct sensor_value range = { .val1 = 4, .val2 = 0 };
	(void)sensor_attr_set(imu, SENSOR_CHAN_ACCEL_XYZ,
			      SENSOR_ATTR_FULL_SCALE, &range);

	struct sensor_trigger trig = {
		.type = SENSOR_TRIG_MOTION,
		.chan = SENSOR_CHAN_ACCEL_XYZ,
	};
	int err = sensor_trigger_set(imu, &trig, motion_trigger);

	if (err) {
		/* driver built without trigger support: wake still works via
		 * the button; log loudly so the power story stays honest */
		LOG_WRN("any-motion trigger unavailable (%d)", err);
	}
	return 0;
}

static void step_work_handler(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(step_work, step_work_handler);

int jr_motion_arm_wake(void)
{
	/* low ODR + any-motion interrupt armed = IMU low-power mode */
	(void)k_work_cancel_delayable(&step_work);
	return set_accel(25, "idle/any-motion");
}

int jr_motion_active(void)
{
	int err = set_accel(50, "active");

	/* sample at the ODR; no-op if the work is already scheduled */
	(void)k_work_schedule(&step_work, K_MSEC(STEP_SAMPLE_MS));
	return err;
}

/* --- tiny step estimator: magnitude peak detection with hysteresis ------ */
#define STEP_THRESH_MG   1150   /* |a| must exceed this (milli-g) */
#define STEP_RESET_MG    1050   /* and drop below this before the next step */
#define STEP_MIN_MS      280    /* max ~3.5 steps/s */

static void sample_step(void)
{
	static bool above;
	static int64_t last_step_ms;
	struct sensor_value acc[3];

	if (sensor_sample_fetch_chan(imu, SENSOR_CHAN_ACCEL_XYZ)) {
		return;
	}
	if (sensor_channel_get(imu, SENSOR_CHAN_ACCEL_XYZ, acc)) {
		return;
	}

	/* magnitude^2 in (m/s^2)^2, compared against thresholds in mg */
	int64_t mx = sensor_value_to_milli(&acc[0]);
	int64_t my = sensor_value_to_milli(&acc[1]);
	int64_t mz = sensor_value_to_milli(&acc[2]);
	int64_t mag2 = mx * mx + my * my + mz * mz;      /* (mm/s^2)^2 */

	/* 1 g = 9806 mm/s^2 */
	int64_t th_hi = (int64_t)STEP_THRESH_MG * 9806 / 1000;
	int64_t th_lo = (int64_t)STEP_RESET_MG * 9806 / 1000;

	th_hi *= th_hi;
	th_lo *= th_lo;

	int64_t now = k_uptime_get();

	if (!above && mag2 > th_hi) {
		above = true;
		if (now - last_step_ms > STEP_MIN_MS) {
			jr_status.steps++;
			last_step_ms = now;
		}
	} else if (above && mag2 < th_lo) {
		above = false;
	}
}

static void step_work_handler(struct k_work *work)
{
	ARG_UNUSED(work);
	sample_step();
	(void)k_work_schedule(&step_work, K_MSEC(STEP_SAMPLE_MS));
}
