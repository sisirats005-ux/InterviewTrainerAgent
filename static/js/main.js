/**
 * Interview Trainer Agent - Core Interaction Script
 * Implementation of premium Tailwind UI updates, dark-mode toggle, and checklist handlers.
 */

document.addEventListener("DOMContentLoaded", () => {
    
    // ==========================================================================
    // 1. DYNAMIC CHECKLIST ACTIONS (Notion style checkboxes)
    // ==========================================================================
    const checklistItems = document.querySelectorAll(".checklist-item");
    checklistItems.forEach(item => {
        item.addEventListener("click", () => {
            item.classList.toggle("checked");
            
            const isChecked = item.classList.contains("checked");
            const checkbox = item.querySelector(".checklist-checkbox");
            const title = item.querySelector(".checklist-title");
            
            if (checkbox) {
                if (isChecked) {
                    checkbox.classList.add("bg-emerald-500", "border-emerald-500");
                    checkbox.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check text-white"><path d="M20 6 9 17l-5-5"/></svg>';
                } else {
                    checkbox.classList.remove("bg-emerald-500", "border-emerald-500");
                    checkbox.innerHTML = '';
                }
            }
            
            if (title) {
                if (isChecked) {
                    title.classList.add("line-through", "text-slate-400");
                } else {
                    title.classList.remove("line-through", "text-slate-400");
                }
            }
        });
    });

    // ==========================================================================
    // 2. FILE UPLOAD DROPZONE LOGIC & DRAG FEEDBACK
    // ==========================================================================
    const uploadZone = document.getElementById("upload-zone");
    const resumeInput = document.getElementById("resume-input");
    const fileInfo = document.getElementById("file-info");
    const fileNameText = document.getElementById("file-name-text");
    const trainerForm = document.getElementById("trainer-form");
    const overlay = document.getElementById("loading-overlay");

    if (uploadZone && resumeInput) {
        uploadZone.addEventListener("click", () => resumeInput.click());

        ["dragenter", "dragover"].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                uploadZone.classList.add("bg-slate-50", "border-emerald-500");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                uploadZone.classList.remove("bg-slate-50", "border-emerald-500");
            }, false);
        });

        uploadZone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length) {
                resumeInput.files = files;
                handleSelectedFile(files[0]);
            }
        });

        resumeInput.addEventListener("change", () => {
            if (resumeInput.files.length) {
                handleSelectedFile(resumeInput.files[0]);
            }
        });
    }

    function handleSelectedFile(file) {
        if (!fileInfo || !fileNameText) return;
        
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext !== "pdf") {
            alert("Security Error: Only valid PDF documents are supported for resume upload.");
            if (resumeInput) resumeInput.value = "";
            fileInfo.classList.add("hidden");
            return;
        }
        
        if (file.size > 4 * 1024 * 1024) {
            alert("Upload Limit: Resume size exceeds the 4MB restriction.");
            if (resumeInput) resumeInput.value = "";
            fileInfo.classList.add("hidden");
            return;
        }

        const sizeKb = (file.size / 1024).toFixed(1);
        fileNameText.textContent = `${file.name} (${sizeKb} KB)`;
        fileInfo.classList.remove("hidden");
    }

    // Trigger overlay steps on form submit
    if (trainerForm && overlay) {
        trainerForm.addEventListener("submit", (e) => {
            if (!resumeInput.files.length) {
                alert("Please select a resume file first.");
                e.preventDefault();
                return;
            }
            overlay.style.display = "flex";
            startLoaderStepper();
        });
    }

    function startLoaderStepper() {
        const steps = [
            { id: "step-1", duration: 700 },
            { id: "step-2", duration: 1100 },
            { id: "step-3", duration: 1100 },
            { id: "step-4", duration: 1400 },
            { id: "step-5", duration: 2500 },
            { id: "step-6", duration: 2000 }
        ];

        let currentIdx = 0;

        function runStep() {
            if (currentIdx >= steps.length) return;
            const step = steps[currentIdx];
            const currentEl = document.getElementById(step.id);
            if (!currentEl) return;

            currentEl.classList.remove("opacity-40");
            currentEl.classList.add("opacity-100");
            const indicator = currentEl.querySelector(".stepper-indicator");
            if (indicator) {
                indicator.classList.add("border-emerald-500", "text-emerald-500");
                indicator.innerHTML = '<svg class="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
            }

            setTimeout(() => {
                currentEl.classList.add("opacity-80");
                if (indicator) {
                    indicator.classList.remove("text-emerald-500");
                    indicator.classList.add("bg-emerald-500", "border-emerald-500", "text-white");
                    indicator.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';
                }

                currentIdx++;
                if (currentIdx < steps.length) {
                    runStep();
                }
            }, step.duration);
        }

        runStep();
    }

    // ==========================================================================
    // 3. MULTI-TAB CONTROLS (Tailwind / CSS visibility based)
    // ==========================================================================
    const tabButtons = document.querySelectorAll(".tab-btn-carbon");
    const tabPanes = document.querySelectorAll(".tab-pane-carbon");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => {
                b.classList.remove("active", "bg-white", "text-slate-900", "border", "border-slate-200", "shadow-sm", "dark:bg-slate-800", "dark:text-white", "dark:border-slate-700");
                b.classList.add("text-slate-500", "hover:text-slate-900", "hover:bg-slate-50", "dark:text-slate-400", "dark:hover:text-white", "dark:hover:bg-slate-800");
                b.setAttribute("aria-selected", "false");
            });
            tabPanes.forEach(p => p.classList.add("hidden"));

            btn.classList.remove("text-slate-500", "hover:text-slate-900", "hover:bg-slate-50", "dark:text-slate-400", "dark:hover:text-white", "dark:hover:bg-slate-800");
            btn.classList.add("active", "bg-white", "text-slate-900", "border", "border-slate-200", "shadow-sm", "dark:bg-slate-800", "dark:text-white", "dark:border-slate-700");
            btn.setAttribute("aria-selected", "true");
            
            const target = btn.getAttribute("data-tab-target");
            const pane = document.querySelector(target);
            if (pane) pane.classList.remove("hidden");
        });
    });

    // ==========================================================================
    // 4. CIRCULAR SVG PROGRESSION RINGS
    // ==========================================================================
    const ring = document.getElementById("circular-progress-ring");
    const scoreVal = document.getElementById("score-text-val");
    if (ring && scoreVal) {
        const score = parseInt(scoreVal.textContent, 10) || 0;
        const circumference = 301.6;
        const offset = circumference - (score / 100) * circumference;
        
        setTimeout(() => {
            ring.style.strokeDashoffset = offset;
        }, 200);
    }

    // ==========================================================================
    // 5. LIGHT / DARK SYSTEM THEME SWITCHER
    // ==========================================================================
    const themeToggle = document.getElementById("theme-toggle");
    
    function applyDarkTheme() {
        document.body.classList.add("dark-theme");
        document.documentElement.classList.add("dark");
        if (themeToggle) {
            themeToggle.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-sun text-amber-500"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>';
        }
    }

    function applyLightTheme() {
        document.body.classList.remove("dark-theme");
        document.documentElement.classList.remove("dark");
        if (themeToggle) {
            themeToggle.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-moon text-slate-500"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>';
        }
    }

    if (localStorage.getItem("theme") === "dark") {
        applyDarkTheme();
    } else {
        applyLightTheme();
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const isDark = document.documentElement.classList.contains("dark");
            if (isDark) {
                localStorage.setItem("theme", "light");
                applyLightTheme();
            } else {
                localStorage.setItem("theme", "dark");
                applyDarkTheme();
            }
        });
    }

    // Mobile responsive sidebar menu toggle
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    const sidebarNav = document.getElementById("sidebar-nav");
    if (mobileMenuBtn && sidebarNav) {
        mobileMenuBtn.addEventListener("click", () => {
            sidebarNav.classList.toggle("hidden");
            sidebarNav.classList.toggle("flex");
        });
    }
});
