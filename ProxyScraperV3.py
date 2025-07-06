import aiohttp
import asyncio
import random
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, StringVar, IntVar
from colorama import Fore, init
import os
import sys
import threading
from fake_useragent import UserAgent

# Initialize
init()
ua = UserAgent()

# Configuration
TEST_URL = "http://www.google.com"
TIMEOUT = 10
MAX_CONCURRENT = 200
WORKING_PROXIES = {'http': [], 'socks4': [], 'socks5': []}
FAILED_PROXIES = {'http': [], 'socks4': [], 'socks5': []}
SCRAPING_ACTIVE = False
CURRENT_PROTOCOL = 'http'

class ProxyScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Proxy Scraper v3.0")
        self.root.geometry("900x700")
        self.setup_ui()
        
    def setup_ui(self):
        # Control Frame
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        # Protocol Selection
        ttk.Label(control_frame, text="Protocol:").grid(row=0, column=0, sticky=tk.W)
        self.protocol_var = StringVar(value="http")
        protocols = [('HTTP', 'http'), ('SOCKS4', 'socks4'), ('SOCKS5', 'socks5')]
        for i, (text, val) in enumerate(protocols):
            ttk.Radiobutton(control_frame, text=text, variable=self.protocol_var, 
                           value=val).grid(row=0, column=i+1, sticky=tk.W)
        
        # Settings
        ttk.Label(control_frame, text="Duration (min):").grid(row=1, column=0, sticky=tk.W)
        self.duration_var = StringVar(value="5")
        ttk.Entry(control_frame, textvariable=self.duration_var, width=5).grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(control_frame, text="Max Threads:").grid(row=1, column=2, sticky=tk.W)
        self.threads_var = StringVar(value="200")
        ttk.Entry(control_frame, textvariable=self.threads_var, width=5).grid(row=1, column=3, sticky=tk.W)
        
        ttk.Label(control_frame, text="Timeout (s):").grid(row=1, column=4, sticky=tk.W)
        self.timeout_var = StringVar(value="10")
        ttk.Entry(control_frame, textvariable=self.timeout_var, width=5).grid(row=1, column=5, sticky=tk.W)
        
        # Buttons
        self.start_btn = ttk.Button(control_frame, text="Start", command=self.start_scraping)
        self.start_btn.grid(row=1, column=6, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.grid(row=1, column=7, padx=5)
        
        self.save_btn = ttk.Button(control_frame, text="Save Proxies", command=self.save_proxies, state=tk.DISABLED)
        self.save_btn.grid(row=1, column=8, padx=5)
        
        # Stats Frame
        stats_frame = ttk.Frame(self.root, padding="10")
        stats_frame.pack(fill=tk.X)
        
        # Stats for each protocol
        self.stats_vars = {}
        for i, protocol in enumerate(['http', 'socks4', 'socks5']):
            frame = ttk.Frame(stats_frame)
            frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            
            ttk.Label(frame, text=protocol.upper(), font=('Arial', 10, 'bold')).pack()
            
            ttk.Label(frame, text="Working:").pack(anchor=tk.W)
            self.stats_vars[f'{protocol}_working'] = StringVar(value="0")
            ttk.Label(frame, textvariable=self.stats_vars[f'{protocol}_working']).pack(anchor=tk.W)
            
            ttk.Label(frame, text="Failed:").pack(anchor=tk.W)
            self.stats_vars[f'{protocol}_failed'] = StringVar(value="0")
            ttk.Label(frame, textvariable=self.stats_vars[f'{protocol}_failed']).pack(anchor=tk.W)
            
            ttk.Label(frame, text="Success Rate:").pack(anchor=tk.W)
            self.stats_vars[f'{protocol}_rate'] = StringVar(value="0%")
            ttk.Label(frame, textvariable=self.stats_vars[f'{protocol}_rate']).pack(anchor=tk.W)
        
        # Time left
        time_frame = ttk.Frame(stats_frame)
        time_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Label(time_frame, text="Time Left:").pack()
        self.time_var = StringVar(value="0s")
        ttk.Label(time_frame, textvariable=self.time_var, font=('Arial', 10, 'bold')).pack()
        
        # Console Output
        console_frame = ttk.Frame(self.root, padding="10")
        console_frame.pack(fill=tk.BOTH, expand=True)
        
        self.console = scrolledtext.ScrolledText(
            console_frame,
            wrap=tk.WORD,
            width=100,
            height=25,
            font=('Consolas', 10)
        )
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.tag_config('success', foreground='green')
        self.console.tag_config('error', foreground='red')
        self.console.tag_config('info', foreground='blue')
        self.console.tag_config('warning', foreground='orange')
        
        # Progress Bar
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, padx=10, pady=5)
    
    def log(self, message, level='info'):
        """Add message to console with colored tag"""
        self.console.insert(tk.END, message + "\n", level)
        self.console.see(tk.END)
        self.root.update_idletasks()
    
    def update_stats(self, protocol=None):
        """Update statistics display for specific protocol or all"""
        protocols = [protocol] if protocol else ['http', 'socks4', 'socks5']
        
        for proto in protocols:
            working = len(WORKING_PROXIES[proto])
            failed = len(FAILED_PROXIES[proto])
            total = working + failed
            rate = (working / total * 100) if total > 0 else 0
            
            self.stats_vars[f'{proto}_working'].set(str(working))
            self.stats_vars[f'{proto}_failed'].set(str(failed))
            self.stats_vars[f'{proto}_rate'].set(f"{rate:.1f}%")
    
    def start_scraping(self):
        """Start the scraping process"""
        global SCRAPING_ACTIVE, MAX_CONCURRENT, TIMEOUT, CURRENT_PROTOCOL
        
        try:
            duration_min = float(self.duration_var.get())
            MAX_CONCURRENT = int(self.threads_var.get())
            TIMEOUT = int(self.timeout_var.get())
            CURRENT_PROTOCOL = self.protocol_var.get()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for settings")
            return
        
        SCRAPING_ACTIVE = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)
        
        WORKING_PROXIES[CURRENT_PROTOCOL].clear()
        FAILED_PROXIES[CURRENT_PROTOCOL].clear()
        self.console.delete(1.0, tk.END)
        self.update_stats(CURRENT_PROTOCOL)
        
        self.log(f"Starting {CURRENT_PROTOCOL.upper()} proxy scraper for {duration_min} minutes", 'info')
        self.log(f"Threads: {MAX_CONCURRENT}, Timeout: {TIMEOUT}s", 'info')
        
        # Start scraping in background thread
        scraping_thread = threading.Thread(
            target=self.run_scraping,
            args=(duration_min * 60,),
            daemon=True
        )
        scraping_thread.start()
        
        # Start stats updater
        self.update_stats_display()
    
    def stop_scraping(self):
        """Stop the scraping process"""
        global SCRAPING_ACTIVE
        SCRAPING_ACTIVE = False
        self.log("Stopping scraper...", 'warning')
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL if WORKING_PROXIES[CURRENT_PROTOCOL] else tk.DISABLED)
    
    def update_stats_display(self):
        """Periodically update stats and progress bar"""
        if SCRAPING_ACTIVE:
            self.update_stats(CURRENT_PROTOCOL)
            self.root.after(1000, self.update_stats_display)
    
    def save_proxies(self):
        """Save working proxies to file"""
        if not WORKING_PROXIES[CURRENT_PROTOCOL]:
            messagebox.showwarning("Warning", "No proxies to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"{CURRENT_PROTOCOL}_proxies.txt"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    for proxy, latency in sorted(WORKING_PROXIES[CURRENT_PROTOCOL], key=lambda x: x[1]):
                        f.write(f"{proxy}\n")
                
                self.log(f"Saved {len(WORKING_PROXIES[CURRENT_PROTOCOL])} {CURRENT_PROTOCOL.upper()} proxies to {file_path}", 'success')
                messagebox.showinfo("Success", f"Saved {len(WORKING_PROXIES[CURRENT_PROTOCOL])} proxies to {file_path}")
            except Exception as e:
                self.log(f"Error saving proxies: {str(e)}", 'error')
                messagebox.showerror("Error", f"Failed to save proxies: {str(e)}")
    
    def run_scraping(self, duration):
        """Main scraping function to run in background thread"""
        global SCRAPING_ACTIVE, WORKING_PROXIES, FAILED_PROXIES, CURRENT_PROTOCOL
        
        async def scrape_proxies():
            scraper = ProxyScraper(self, CURRENT_PROTOCOL)
            start_time = time.time()
            end_time = start_time + duration
            
            while SCRAPING_ACTIVE and time.time() < end_time:
                time_left = max(0, end_time - time.time())
                self.time_var.set(f"{int(time_left)}s")
                self.progress['value'] = 100 - (time_left / duration * 100)
                
                self.log(f"Fetching {CURRENT_PROTOCOL.upper()} proxies from sources...", 'info')
                proxies = await scraper.get_all_proxies()
                
                if not proxies:
                    self.log(f"No {CURRENT_PROTOCOL.upper()} proxies found in this round!", 'warning')
                    await asyncio.sleep(5)
                    continue
                
                self.log(f"Found {len(proxies)} {CURRENT_PROTOCOL.upper()} proxies. Testing...", 'info')
                await scraper.test_proxies(proxies)
                
                if SCRAPING_ACTIVE and time.time() < end_time:
                    await asyncio.sleep(2)
            
            self.stop_scraping()
        
        # Run async function in thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scrape_proxies())

class ProxyScraper:
    def __init__(self, gui, protocol):
        self.gui = gui
        self.protocol = protocol
        self.sources = self.get_sources_for_protocol()
    
    def get_sources_for_protocol(self):
        """Return appropriate sources for the selected protocol"""
        base_sources = {
            'http': [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                "https://www.proxy-list.download/api/v1/get?type=http",
                "https://www.proxyscan.io/download?type=http",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
                "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
                "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
            ],
            'socks4': [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
                "https://www.proxy-list.download/api/v1/get?type=socks4",
                "https://www.proxyscan.io/download?type=socks4",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
                "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"
            ],
            'socks5': [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
                "https://www.proxy-list.download/api/v1/get?type=socks5",
                "https://www.proxyscan.io/download?type=socks5",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
                "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
                "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
            ]
        }
        return base_sources.get(self.protocol, [])
    
    async def fetch_proxies(self, session, url):
        if not SCRAPING_ACTIVE:
            return []
            
        try:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        data = await response.json()
                        if 'data' in data:
                            return [f"{p['ip']}:{p['port']}" for p in data['data']]
                        return []
                    else:
                        text = await response.text()
                        proxies = []
                        for line in text.splitlines():
                            line = line.strip()
                            if line and ':' in line and not line.startswith('#'):
                                proxies.append(line)
                        return proxies
        except Exception as e:
            self.gui.log(f"Error fetching {url}: {str(e)}", 'error')
            return []
        return []

    async def get_all_proxies(self):
        connector = aiohttp.TCPConnector(limit=20)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_proxies(session, url) for url in self.sources]
            results = await asyncio.gather(*tasks)
            all_proxies = []
            for proxy_list in results:
                if proxy_list:
                    all_proxies.extend(proxy_list)
            return list(set(all_proxies))  # Remove duplicates

    async def test_proxies(self, proxies):
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        connector = aiohttp.TCPConnector(force_close=True, limit=MAX_CONCURRENT)
        
        async with aiohttp.ClientSession(
            connector=connector,
            headers={'User-Agent': ua.random}
        ) as session:
            tasks = [self.test_proxy(session, proxy, semaphore) for proxy in proxies]
            await asyncio.gather(*tasks)
    
    async def test_proxy(self, session, proxy, semaphore):
        if not SCRAPING_ACTIVE:
            return False
        
        # Validate proxy format
        if ':' not in proxy:
            FAILED_PROXIES[self.protocol].append(proxy)
            self.gui.update_stats(self.protocol)
            return False
        
        proxy_url = f"{self.protocol}://{proxy}"
        
        try:
            async with semaphore:
                start_time = time.time()
                async with session.get(
                    TEST_URL,
                    proxy=proxy_url,
                    timeout=TIMEOUT
                ) as response:
                    if response.status == 200:
                        latency = int((time.time() - start_time) * 1000)  # in ms
                        WORKING_PROXIES[self.protocol].append((proxy, latency))
                        self.gui.log(f"[{self.protocol.upper()}] Working: {proxy} ({latency}ms)", 'success')
                        self.gui.update_stats(self.protocol)
                        return True
        except Exception as e:
            pass
        
        FAILED_PROXIES[self.protocol].append(proxy)
        self.gui.log(f"[{self.protocol.upper()}] Failed: {proxy}", 'error')
        self.gui.update_stats(self.protocol)
        return False

if __name__ == "__main__":
    root = tk.Tk()
    app = ProxyScraperGUI(root)
    root.mainloop()