#define G_LOG_DOMAIN "moga-main"

#include <glib.h>
#include <glib/gprintf.h>
#include <gio/gio.h>

static GDBusConnection *g_connection = NULL;
static guint g_filter_id = 0;

static void signal_cb
(
    GDBusConnection *connection,
    const gchar *sender_name,
    const gchar *object_path,
    const gchar *interface_name,
    const gchar *signal_name,
    GVariant *parameters,
    gpointer user_data)
{
    gchar *s;
    s = g_variant_print(parameters, TRUE);
    g_debug(
        "%s: %s.%s %s",
        object_path,
        interface_name,
        signal_name,
        s
    );
    g_free(s);

    g_assert(g_variant_n_children(parameters) == 3);
    GVariantDict *changed = g_variant_dict_new(g_variant_get_child_value(parameters, 1));
    if (g_variant_dict_contains(changed, "Connected"))
    {
        GVariant *connected = g_variant_dict_lookup_value(
            changed, "Connected", G_VARIANT_TYPE_BOOLEAN
        );
        if (g_variant_get_boolean(connected))
        {
            g_info("Device connected");
        }
        else
        {
            g_info("Device disconnected");
        }
    }
}

static void on_name_appeared(
    GDBusConnection *connection,
    const gchar *name, const gchar *name_owner,
    gpointer user_data
)
{
    g_info("org.bluez appeared");
    g_filter_id = g_dbus_connection_signal_subscribe(
        connection,
        "org.bluez",
        NULL,
        "PropertiesChanged",
        NULL, NULL,
        G_DBUS_SIGNAL_FLAGS_NONE,
        signal_cb,
        NULL, NULL
    );
}

static void on_name_vanished(
    GDBusConnection *connection,
    const gchar *name,
    gpointer user_data
)
{
    g_info("org.bluez vanished");
    if (g_filter_id != 0)
    {
        g_dbus_connection_signal_unsubscribe(
            connection, g_filter_id
        );
        g_filter_id = 0;
    }
}

int main(int argc, char **argv)
{
    GMainLoop *loop = NULL;
    GError *error = NULL;
    guint watcher_id = 0;

    loop = g_main_loop_new(NULL, FALSE);

    g_connection = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &error);
    if (g_connection == NULL)
    {
        g_critical("Error while connecting: %s", error->message);
        g_error_free(error);
        goto cleanup;
    }

    watcher_id = g_bus_watch_name_on_connection(
        g_connection,
        "org.bluez",
        G_BUS_NAME_WATCHER_FLAGS_NONE,
        on_name_appeared,
        on_name_vanished,
        NULL, NULL
    );

    g_main_loop_run(loop);

cleanup:
    g_bus_unwatch_name(watcher_id);
    return 0;
}
