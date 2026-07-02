/*
 * Watch face on the Sharp memory-in-pixel LCD.
 *
 * Power rules: the panel holds a static image at ~µW, so we redraw ONLY
 * when the visible content changes (minute, battery %, steps, charge
 * state). The display rail (VDD_DISP) is a PMIC load switch and can be cut
 * entirely; the ls0xx driver re-inits on power-up. EXTCOMIN's 1 Hz toggle
 * comes from the driver's timer (EXTMODE is strapped high in hardware).
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/device.h>
#include <zephyr/display/cfb.h>
#include <zephyr/drivers/display.h>
#include <zephyr/drivers/regulator.h>

LOG_MODULE_REGISTER(ui, CONFIG_LOG_DEFAULT_LEVEL);

#include "jrwatch.h"

static const struct device *const disp = DEVICE_DT_GET(DT_CHOSEN(zephyr_display));
static const struct device *const lsw_disp =
	DEVICE_DT_GET(DT_NODELABEL(npm1300_lsw_disp));

static bool disp_powered;
static char last_frame[48];

int jr_ui_display_power(bool on)
{
	int err = 0;

	if (on == disp_powered) {
		return 0;
	}
	if (on) {
		err = regulator_enable(lsw_disp);
		if (err == 0) {
			k_msleep(2);            /* panel VDD settle */
			err = cfb_framebuffer_init(disp);
			(void)display_blanking_off(disp);
			last_frame[0] = '\0';   /* force a redraw */
		}
	} else {
		/* drive interface lines low before cutting the rail so the
		 * unpowered panel is never back-fed through its inputs */
		(void)display_blanking_on(disp);
		err = regulator_disable(lsw_disp);
	}
	if (err == 0) {
		disp_powered = on;
	} else {
		LOG_ERR("display power %d: %d", on, err);
	}
	return err;
}

int jr_ui_init(void)
{
	if (!device_is_ready(disp)) {
		LOG_ERR("display not ready");
		return -ENODEV;
	}
	if (!device_is_ready(lsw_disp)) {
		LOG_ERR("display load switch not ready");
		return -ENODEV;
	}
	return 0;
}

void jr_ui_render(void)
{
	char frame[48];
	int64_t up_s = k_uptime_get() / 1000;
	unsigned int hh = (up_s / 3600) % 24;
	unsigned int mm = (up_s / 60) % 60;

	if (!disp_powered) {
		return;
	}

	/* uptime-clock until BLE CTS sync lands (documented follow-up) */
	snprintk(frame, sizeof(frame), "%02u:%02u|%u%%%s|%u", hh, mm,
		 jr_status.battery_pct, jr_status.charging ? "+" : "",
		 jr_status.steps);
	if (strcmp(frame, last_frame) == 0) {
		return;                        /* nothing changed: stay µW */
	}
	strcpy(last_frame, frame);

	char line[24];

	(void)cfb_framebuffer_clear(disp, false);
	snprintk(line, sizeof(line), "%02u:%02u", hh, mm);
	(void)cfb_print(disp, line, 24, 28);
	snprintk(line, sizeof(line), "bat %3u%%%s", jr_status.battery_pct,
		 jr_status.charging ? " chg" : "");
	(void)cfb_print(disp, line, 8, 64);
	snprintk(line, sizeof(line), "%u steps", jr_status.steps);
	(void)cfb_print(disp, line, 8, 88);
	(void)cfb_framebuffer_finalize(disp);
}
