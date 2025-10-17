<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';
  // import { Building2, FileText, Calculator, Send, Menu, X } from 'lucide-svelte';
  
  let sidebarOpen = false;

  const navigation = [
    { 
      name: 'Служебни функции', 
      href: '/companies', 
      description: 'Избор на задължено лице'
    },
    { 
      name: 'Въвеждане', 
      href: '/journals', 
      description: 'Дневници на покупките и продажбите',
      children: [
        { name: 'Дневник на покупките', href: '/journals/purchases' },
        { name: 'Дневник за продажбите', href: '/journals/sales' }
      ]
    },
    { 
      name: 'Внос данни', 
      href: '/import', 
      description: 'Импорт от PaperlessAI'
    },
    { 
      name: 'Справки', 
      href: '/declarations', 
      description: 'Справка-декларация по ЗДДС и VIES'
    },
    { 
      name: 'НАП', 
      href: '/nap', 
      description: 'Подаване и плащания'
    },
  ];

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }
</script>

<div class="min-h-full bg-gray-50">
  <!-- Mobile menu button -->
  <div class="lg:hidden fixed top-4 left-4 z-50">
    <button
      on:click={toggleSidebar}
      class="bg-white p-2 rounded-md shadow-md"
    >
      {#if sidebarOpen}
        ✕
      {:else}
        ☰
      {/if}
    </button>
  </div>

  <!-- Sidebar -->
  <div class="fixed inset-y-0 left-0 z-40 w-64 bg-white shadow-lg transform {sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 transition-transform">
    <div class="flex flex-col h-full">
      <!-- Logo -->
      <div class="flex items-center px-6 py-6 border-b border-gray-200">
        <div class="w-8 h-8 bg-blue-600 rounded text-white flex items-center justify-center font-bold">Д</div>
        <div class="ml-3">
          <h1 class="text-xl font-bold text-gray-900">Дневници</h1>
          <p class="text-sm text-gray-500">VAT System v2.0</p>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-4 py-6 space-y-2">
        {#each navigation as item}
          <div>
            <a
              href={item.href}
              class="flex items-center px-3 py-2 text-sm font-medium rounded-md 
                     {$page.url.pathname.startsWith(item.href) 
                       ? 'bg-blue-50 text-blue-700 border-r-4 border-blue-700' 
                       : 'text-gray-600 hover:bg-gray-50'}"
            >
              <!-- Icon placeholder -->
              {item.name}
            </a>
            
            {#if item.children && $page.url.pathname.startsWith(item.href)}
              <div class="ml-8 mt-2 space-y-1">
                {#each item.children as child}
                  <a
                    href={child.href}
                    class="block px-3 py-2 text-sm text-gray-600 rounded-md hover:bg-gray-50
                           {$page.url.pathname === child.href ? 'bg-blue-50 text-blue-700' : ''}"
                  >
                    {child.name}
                  </a>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </nav>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-200">
        <p class="text-xs text-gray-500">
          Базирано на НАП Дневници v14.02<br>
          Модернизирано за уеб
        </p>
      </div>
    </div>
  </div>

  <!-- Overlay for mobile -->
  {#if sidebarOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div 
      class="lg:hidden fixed inset-0 z-30 bg-black bg-opacity-50"
      on:click={toggleSidebar}
    ></div>
  {/if}

  <!-- Main content -->
  <div class="lg:ml-64 flex flex-col min-h-screen">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200 lg:static lg:bg-white">
      <div class="px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex justify-between items-center">
          <div class="ml-12 lg:ml-0">
            {#if $page.url.pathname === '/'}
              <h1 class="text-2xl font-bold text-gray-900">Начало</h1>
              <p class="text-gray-600">Система за управление на ДДС</p>
            {:else}
              {@const currentNav = navigation.find(nav => $page.url.pathname.startsWith(nav.href))}
              {#if currentNav}
                <h1 class="text-2xl font-bold text-gray-900">{currentNav.name}</h1>
                <p class="text-gray-600">{currentNav.description}</p>
              {/if}
            {/if}
          </div>
          
          <div class="flex items-center space-x-4">
            <!-- Status indicators could go here -->
            <div class="text-sm text-gray-500">
              {new Date().toLocaleDateString('bg-BG')}
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Page content -->
    <main class="flex-1 px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>
  </div>
</div>