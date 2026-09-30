// Addons del servidor (p. ej. ClassicForever_Bots): los anuncia status.json ("addons": [{name, version, url, sha256}]) y el
// launcher los instala o actualiza en _classic_beta_\Interface\AddOns. Solo desde las Releases de este repo, con el
// SHA-256 comprobado, y solo ficheros de addon dentro de la carpeta del addon. Nunca con el juego abierto.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace ForeverLauncher
{
    public sealed class AddonInfo
    {
        public string Name, Version, Url, Sha256;
    }

    public static class AddonInstaller
    {
        public const string UrlPrefix = "https://github.com/defexnicolas/wow-classic-launcher/releases/download/";
        static readonly string[] AllowedExt = { ".lua", ".toc", ".xml", ".png", ".tga", ".blp", ".md", ".txt" };
        const long MaxBytes = 8L * 1024 * 1024;

        public static bool Valid(AddonInfo a)
        {
            return a != null && a.Name != null && Regex.IsMatch(a.Name, @"^[A-Za-z0-9_]{1,64}$")
                && a.Version != null && Regex.IsMatch(a.Version, @"^[0-9A-Za-z.\-]{1,20}$")
                && a.Url != null && a.Url.StartsWith(UrlPrefix, StringComparison.Ordinal) && !a.Url.Contains("..")
                && (a.Sha256 == null || Regex.IsMatch(a.Sha256, @"^[0-9a-fA-F]{64}$"));
        }

        static string AddOnsDir(string gameDir) { return Path.Combine(gameDir, "Interface", "AddOns"); }

        // "## Version: 1.3" del .toc instalado, o null
        public static string InstalledVersion(string gameDir, string name)
        {
            try
            {
                string toc = Path.Combine(AddOnsDir(gameDir), name, name + ".toc");
                if (!File.Exists(toc)) return null;
                foreach (string line in File.ReadAllLines(toc))
                {
                    var m = Regex.Match(line, @"^##\s*Version:\s*(\S+)");
                    if (m.Success) return m.Groups[1].Value;
                }
                return "?";
            }
            catch { return null; }
        }

        // Instala o actualiza lo que haga falta. Devuelve un mensaje por addon tocado (o con error).
        public static async Task<List<Msg>> SyncAsync(string gameDir, IEnumerable<AddonInfo> addons)
        {
            var result = new List<Msg>();
            foreach (var a in addons)
            {
                if (!Valid(a)) continue;
                string have = InstalledVersion(gameDir, a.Name);
                if (have == a.Version) continue;
                try
                {
                    await InstallAsync(gameDir, a);
                    result.Add(new Msg(MsgKind.Good, have == null ? "addon.installed" : "addon.updated", a.Name, a.Version));
                }
                catch (Exception ex)
                {
                    result.Add(new Msg(MsgKind.Warn, "addon.failed", a.Name, ex.Message));
                }
            }
            return result;
        }

        static async Task InstallAsync(string gameDir, AddonInfo a)
        {
            byte[] zip;
            string expected = a.Sha256;
            using (var wc = new WebClient())
            {
                wc.Headers[HttpRequestHeader.UserAgent] = "ClassicForeverLauncher/" + App.Version;
                zip = await wc.DownloadDataTaskAsync(a.Url);
                if (expected == null)   // sin hash en el feed: el .sha256 publicado junto al zip en la misma Release
                    expected = (await wc.DownloadStringTaskAsync(a.Url + ".sha256")).Trim().Split(' ', '\t')[0];
            }
            InstallZip(gameDir, a, zip, expected);
        }

        // Comprueba el hash y el contenido del zip y cambia la carpeta del addon. Separado de la descarga para las pruebas.
        public static void InstallZip(string gameDir, AddonInfo a, byte[] zip, string expected)
        {
            if (zip.Length > MaxBytes) throw new InvalidDataException("zip > 8 MB");
            string got;
            using (var sha = SHA256.Create())
                got = BitConverter.ToString(sha.ComputeHash(zip)).Replace("-", "").ToLowerInvariant();
            if (!string.Equals(got, expected, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("SHA-256 no coincide");

            string addOns = AddOnsDir(gameDir);
            Directory.CreateDirectory(addOns);
            string staging = Path.Combine(addOns, "." + a.Name + ".new");
            if (Directory.Exists(staging)) Directory.Delete(staging, true);
            Directory.CreateDirectory(staging);
            try
            {
                Extract(a, zip, staging);
            }
            catch
            {
                try { Directory.Delete(staging, true); } catch { }
                throw;
            }
            // cambio: la carpeta vieja se aparta, la nueva entra, y la vieja se borra
            string target = Path.Combine(addOns, a.Name);
            string old = Path.Combine(addOns, "." + a.Name + ".old");
            if (Directory.Exists(old)) Directory.Delete(old, true);
            if (Directory.Exists(target)) Directory.Move(target, old);
            Directory.Move(staging, target);
            if (Directory.Exists(old)) try { Directory.Delete(old, true); } catch { }
        }

        static void Extract(AddonInfo a, byte[] zip, string staging)
        {
            string stagingFull = Path.GetFullPath(staging) + Path.DirectorySeparatorChar;
            long total = 0;
            using (var ms = new MemoryStream(zip))
            using (var archive = new ZipArchive(ms, ZipArchiveMode.Read))
            {
                foreach (var e in archive.Entries)
                {
                    string rel = e.FullName.Replace('\\', '/');
                    if (rel.EndsWith("/")) continue;   // carpetas
                    if (!rel.StartsWith(a.Name + "/", StringComparison.Ordinal))
                        throw new InvalidDataException("fichero fuera de " + a.Name + ": " + rel);
                    if (!AllowedExt.Contains(Path.GetExtension(rel).ToLowerInvariant()))
                        throw new InvalidDataException("tipo de fichero no permitido: " + rel);
                    string dest = Path.GetFullPath(Path.Combine(staging, rel.Substring(a.Name.Length + 1)));
                    if (!dest.StartsWith(stagingFull, StringComparison.OrdinalIgnoreCase))
                        throw new InvalidDataException("ruta no permitida: " + rel);
                    total += e.Length;
                    if (total > MaxBytes * 4) throw new InvalidDataException("addon demasiado grande");
                    Directory.CreateDirectory(Path.GetDirectoryName(dest));
                    e.ExtractToFile(dest, true);
                }
            }
            if (!File.Exists(Path.Combine(staging, a.Name + ".toc")))
                throw new InvalidDataException("falta " + a.Name + ".toc");
        }
    }
}
