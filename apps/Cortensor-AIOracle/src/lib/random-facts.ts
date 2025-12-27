export interface RandomFact {
  title: string
  url: string
  snippet: string
  reliability: 'high' | 'medium' | 'low' | 'unknown'
  publisher?: string
  publishedAt?: string
  source?: string
  verdict: 'Yes' | 'No'
  question?: string
  answer?: string
}

const TAVILY_URL = 'https://api.tavily.com/search'

// Explicit yes/no claim-style prompts grouped by category (50 each)
const YES_NO_PROMPT_CATEGORIES: Record<string, string[]> = {
  science: [
    'Is lightning hotter than the surface of the sun?',
    'Do sharks sleep?',
    'Is glass an amorphous solid?',
    'Can sound travel in space?',
    'Is absolute zero unattainable?',
    'Do penguins live in the Arctic?',
    'Is DNA a double helix?',
    'Do plants perform photosynthesis at night?',
    'Is water denser at 4 degrees Celsius than at 0 degrees?',
    'Is blood ever blue inside the body?',
    'Do bananas contain radioactive potassium?',
    'Can humans digest cellulose?',
    'Is copper a better conductor than iron?',
    'Do all metals conduct electricity?',
    'Is graphene one atom thick?',
    'Do viruses have their own metabolism?',
    'Is the speed of light constant in vacuum?',
    'Can humans see UV light unaided?',
    'Is helium lighter than air?',
    'Do magnets lose strength when heated?',
    'Is rusting an oxidation reaction?',
    'Is charcoal mostly carbon?',
    'Is dry ice solid carbon dioxide?',
    'Can sugar dissolve faster in hot water?',
    'Is tungsten the metal with the highest melting point?',
    'Is ammonia a base?',
    'Do ants have lungs?',
    'Is Pluto classified as a dwarf planet?',
    'Is the Pacific Ocean the deepest ocean?',
    'Do earthquakes occur at plate boundaries?',
    'Is photosynthesis endothermic?',
    'Is the ozone hole mainly over Antarctica?',
    'Is carbon the basis of organic chemistry?',
    'Are proteins made of amino acids?',
    'Is lactose a disaccharide?',
    'Is boiling a liquid-to-gas phase change?',
    'Do catalysts lower activation energy?',
    'Is neon a noble gas?',
    'Is graphite used as a lubricant?',
    'Is salt water a homogeneous mixture?',
    'Is vinegar acidic?',
    'Does vitamin D require sunlight to synthesize in skin?',
    'Is insulin a hormone?',
    'Is adrenaline also called epinephrine?',
    'Do fungi have cell walls?',
    'Is diffusion driven by concentration gradients?',
    'Is osmosis specific to water movement?',
    'Is silicon a semiconductor?',
    'Can liquid water exist on Mars today?',
    'Is Mercury the closest planet to the sun?',
    'Is Earth the only planet with liquid surface water currently?'
  ],
  general: [
    'Is the Great Wall of China visible from space with the naked eye?',
    'Is Mount Everest the tallest mountain above sea level?',
    'Do camels store water in their humps?',
    'Is sushi always raw fish?',
    'Is New York the capital of the USA?',
    'Is the equator the longest line of latitude?',
    'Is English the most spoken native language?',
    'Is the Sahara the largest desert in the world?',
    'Is Africa the second largest continent?',
    'Is Europe a separate tectonic plate?',
    'Is coffee dehydrating?',
    'Is water wet?',
    'Is Australia both a country and a continent?',
    'Is Canada the country with the most lakes?',
    'Is Antarctica a desert by precipitation?',
    'Is the Dead Sea below sea level?',
    'Is Greenland mostly ice-covered?',
    'Is the Amazon rainforest the largest tropical rainforest?',
    'Is the Nile the longest river?',
    'Is the Indian Ocean the warmest ocean?',
    'Is chocolate toxic to dogs?',
    'Is copper used in most household wiring?',
    'Is plastic biodegradable by default?',
    'Is aluminum magnetic?',
    'Is gold denser than lead?',
    'Is diamond the hardest natural material?',
    'Is sand mostly silica?',
    'Is marble a metamorphic rock?',
    'Is glass recyclable?',
    'Is Wi-Fi an acronym?',
    'Is a tomato a fruit botanically?',
    'Is a pumpkin a berry botanically?',
    'Is honeybee the only insect making edible honey for humans?',
    'Is Friday named after a Norse goddess?',
    'Is February the only month that can miss a full moon?',
    'Is noon when the sun is highest everywhere?',
    'Is the International Date Line straight?',
    'Is UTC the same as GMT?',
    'Is Celsius an SI base unit?',
    'Is a byte 8 bits?',
    'Is JPEG lossless?',
    'Is PNG lossless?',
    'Is PDF a raster format?',
    'Is Bluetooth named after a king?',
    'Is Morse code still used?',
    'Is Esperanto a natural language?',
    'Is Iceland greener than Greenland?',
    'Is Venice built on islands?',
    'Is Rome older than Athens?',
    'Is the UK made of four countries?'
  ],
  history: [
    'Did the Roman Empire fall in 476 AD?',
    'Was Cleopatra ethnically Egyptian Greek?',
    'Did the Mongol Empire reach Europe?',
    'Was the Great Fire of London in 1666?',
    'Did World War I start in 1914?',
    'Did the Berlin Wall fall in 1989?',
    'Was Machu Picchu built by the Inca?',
    'Did the Wright brothers fly in 1903?',
    'Was Julius Caesar assassinated on the Ides of March?',
    'Did Napoleon lose at Waterloo?',
    'Did the Titanic sink in 1912?',
    'Was the Renaissance centered in Italy?',
    'Did Vikings reach North America?',
    'Was the Black Death in the 14th century?',
    'Did the US land on the moon in 1969?',
    'Was paper invented in China?',
    'Did Gutenberg invent the printing press?',
    'Was Genghis Khan born in Mongolia?',
    'Was the Cold War a conflict between NATO and the Warsaw Pact?',
    'Did the Aztecs build Tenochtitlan?',
    'Was the French Revolution in 1789?',
    'Did ancient Egyptians use papyrus?',
    'Was the Silk Road a single road?',
    'Did the Apollo 13 crew survive?',
    'Was Constantinople renamed Istanbul?',
    'Did the Ottoman Empire last until the 20th century?',
    'Was Stonehenge built in the Neolithic?',
    'Did the Mayans predict the world ending in 2012?',
    'Was the League of Nations before the UN?',
    'Did World War II end in 1945?',
    'Was Sputnik the first artificial satellite?',
    'Did ancient Rome use concrete?',
    'Was the Suez Canal opened in the 19th century?',
    'Was the Great Depression in the 1930s?',
    'Did Alexander the Great conquer Persia?',
    'Was the Colosseum used for gladiator games?',
    'Did the Qin dynasty unify China?',
    'Was tea first cultivated in China?',
    'Did Marco Polo reach China?',
    'Was the Trojan War historical fact?',
    'Did the Han dynasty establish the Silk Road?',
    'Was the Magna Carta signed in 1215?',
    'Was the Spanish Armada defeated in 1588?',
    'Did the Meiji Restoration modernize Japan?',
    'Did Rome fall before the Eastern Empire?',
    'Was the Industrial Revolution in the 18th century?',
    'Did the Persian Empire precede Alexander?',
    'Did the Incas use quipus as records?',
    'Did the Berlin Airlift occur in 1948?',
    'Was the Cuban Missile Crisis in 1962?'
  ],
  technology: [
    'Is TCP a transport layer protocol?',
    'Is UDP connectionless?',
    'Is HTML a programming language?',
    'Is CSS Turing complete by design?',
    'Is JavaScript single-threaded by default?',
    'Is Python statically typed?',
    'Is Rust a systems programming language?',
    "Is Moore's Law about transistor counts doubling?",
    'Is 5G faster than 4G?',
    'Is Bluetooth low energy different from classic Bluetooth?',
    'Is IPv6 128-bit addressing?',
    'Is RAID 0 fault tolerant?',
    'Is SSD faster than HDD?',
    'Is AES a symmetric cipher?',
    'Is RSA a symmetric cipher?',
    'Is SHA-256 a hashing algorithm?',
    'Is Git a distributed version control system?',
    'Is Docker a type-1 hypervisor?',
    'Is Kubernetes an orchestrator?',
    'Is HDMI digital only?',
    'Is DisplayPort capable of daisy-chaining?',
    'Is VRAM used by GPUs?',
    'Is RAM non-volatile memory?',
    'Is an IP address layer 3?',
    'Is MAC address layer 2?',
    'Is ARP used for IPv6?',
    'Is SMTP for email sending?',
    'Is POP3 for email retrieval?',
    'Is IMAP stateless?',
    'Is REST strictly tied to HTTP?',
    'Is JSON a binary format?',
    'Is BSON binary JSON?',
    'Is WebAssembly binary?',
    'Is TLS successor to SSL?',
    'Is FTP encrypted by default?',
    'Is SFTP built on SSH?',
    'Is NFC shorter range than Wi-Fi?',
    'Is LiDAR using lasers?',
    'Is OLED self-emissive?',
    'Is QLED based on quantum dots?',
    'Is GPS dependent on ground towers?',
    'Is IPv4 exhausted?',
    'Is RAID 1 mirroring?',
    'Is RAID 5 tolerant to one disk failure?',
    'Is HDMI carrying audio?',
    'Is USB-C reversible?',
    'Is Lightning proprietary to Apple?',
    'Is PCIe a serial bus?',
    'Is SATA faster than PCIe?',
    'Is NVMe using PCIe lanes?',
    'Is AI a subset of machine learning?'
  ],
  health: [
    'Does vitamin C cure the common cold?',
    'Is fever always harmful?',
    'Is honey anti-bacterial?',
    'Is dehydration possible from drinking too much water?',
    'Is BMI a perfect health metric?',
    'Is high blood pressure always symptomatic?',
    'Is type 2 diabetes reversible through lifestyle?',
    'Do vaccines cause autism?',
    'Is garlic an antibiotic?',
    'Is intermittent fasting safe for everyone?',
    'Is sleep before midnight always better?',
    'Do you need 8 glasses of water daily?',
    'Is cholesterol always bad?',
    'Is brown sugar healthier than white sugar?',
    'Is spot reduction fat loss possible?',
    'Is stretching before exercise always required?',
    'Is walking 10k steps mandatory for health?',
    'Is sitting the new smoking?',
    'Is sunscreen needed indoors?',
    'Is blue light always harmful to sleep?',
    'Is gluten harmful to everyone?',
    'Is lactose intolerance an allergy?',
    'Is MSG dangerous for most people?',
    'Is caffeine a diuretic?',
    'Is dark chocolate heart-healthy?',
    'Is fish oil proven to prevent heart disease?',
    'Is salt always bad for blood pressure?',
    'Is meditation proven to reduce stress?',
    'Is yoga only stretching?',
    'Is weight training bad for joints?',
    'Is cardio the only way to lose fat?',
    'Is breakfast the most important meal?',
    'Is late-night eating always fattening?',
    'Is fruit juice as healthy as whole fruit?',
    'Is alcohol in moderation good for the heart?',
    'Is vaping safer than smoking?',
    'Is secondhand smoke harmless outdoors?',
    'Is herbal medicine always safe?',
    'Is vitamin D only from sun exposure?',
    'Is protein intake dangerous for kidneys in healthy people?',
    'Is sitting with bad posture harmless?',
    'Is cracking knuckles causing arthritis?',
    'Is sugar more addictive than cocaine?',
    'Is red meat classified as carcinogenic?',
    'Is fluoride in water harmful?',
    'Is cold weather causing colds?',
    'Is hand sanitizer better than soap?',
    'Is milk necessary for strong bones?',
    'Is organic food pesticide-free?',
    'Is detox dieting scientifically supported?'
  ],
  space: [
    'Can you see the Great Wall of China from space unaided?',
    'Is Venus hotter than Mercury?',
    'Is Mars red because of rust?',
    'Is Jupiter a gas giant?',
    'Do astronauts grow taller in microgravity?',
    'Is the moon moving away from Earth?',
    'Is there weather on the moon?',
    'Is a day on Venus longer than its year?',
    'Is Saturn the only planet with rings?',
    'Is the sun a yellow dwarf?',
    'Is space completely silent?',
    'Is the ISS in geostationary orbit?',
    'Is Pluto still a planet?',
    'Is Europa believed to have a subsurface ocean?',
    'Is Titan larger than Mercury?',
    'Is the Kuiper Belt beyond Neptune?',
    'Is a black hole a hole?',
    'Do all stars end as black holes?',
    'Is the Milky Way a spiral galaxy?',
    'Is Andromeda moving toward the Milky Way?',
    'Is the Hubble constant truly constant?',
    'Is dark matter directly observed?',
    'Is the speed of light a universal speed limit?',
    'Is there gravity in space?',
    'Is the North Star the brightest star?',
    'Is a shooting star a real star?',
    'Is a comet made mostly of ice?',
    'Is the moon tidally locked to Earth?',
    'Is geostationary orbit the same as geosynchronous?',
    'Is space a perfect vacuum?',
    'Is the James Webb Space Telescope in low Earth orbit?',
    'Is Neptune visible to the naked eye?',
    'Is Uranus tilted on its side?',
    'Is Ceres an asteroid or a dwarf planet?',
    'Is Phobos a moon of Mars?',
    'Is Betelgeuse a red supergiant?',
    'Is Polaris at the celestial equator?',
    'Is a light-year a measure of time?',
    'Is Mercury tidally locked to the sun?',
    'Is there liquid water on the sun?',
    'Is an eclipse only solar?',
    'Is the Van Allen belt dangerous to satellites?',
    'Is ISS speed about 28,000 km/h?',
    'Is Lagrange point L2 behind Earth relative to the sun?',
    'Is a parsec shorter than a light-year?',
    'Is the heliosphere the sun’s magnetic bubble?',
    'Is Proxima Centauri the closest star to the sun?',
    'Is the Oort cloud closer than Pluto?',
    'Is Voyager 1 still communicating?',
    'Is the Kuiper Belt the source of most long-period comets?'
  ]
}

const reliabilityFromDomain = (domain: string | undefined): RandomFact['reliability'] => {
  if (!domain) return 'unknown'
  const d = domain.toLowerCase()
  const high = ['reuters.com', 'apnews.com', 'bbc.com', 'nature.com', 'science.org', 'nasa.gov', 'who.int', 'cdc.gov']
  if (high.some(h => d.endsWith(h) || d.includes(h))) return 'high'
  if (/(news|journal|times|post|guardian|forbes|bloomberg|wsj|ft\.com)/i.test(d)) return 'medium'
  return 'low'
}

const ALL_YES_NO_PROMPTS = Object.values(YES_NO_PROMPT_CATEGORIES).flat()

const pickQuery = () => ALL_YES_NO_PROMPTS[Math.floor(Math.random() * ALL_YES_NO_PROMPTS.length)]

const deriveVerdict = (text?: string | null): 'Yes' | 'No' | null => {
  if (!text) return null
  const t = text.toLowerCase()
  if (/(\bno\b|not true|false|incorrect|myth|hoax|debunk)/i.test(t)) return 'No'
  if (/(\byes\b|true|correct|indeed|confirmed|factual)/i.test(t)) return 'Yes'
  return null
}

const shuffle = <T,>(arr: T[]): T[] => {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

const normalizeUrl = (raw: string): string => {
  let u = raw.trim().replace(/[)\]\.,;:'"\s]+$/g, '')
  try {
    const urlObj = new URL(u)
    const toDelete: string[] = []
    urlObj.searchParams.forEach((_, k) => {
      if (/^utm_|^ref$|^fbclid$|^gclid$|^mc_cid$|^mc_eid$/i.test(k)) toDelete.push(k)
    })
    toDelete.forEach(k => urlObj.searchParams.delete(k))
    urlObj.hash = ''
    return urlObj.toString()
  } catch {
    return u
  }
}

const domainFromUrl = (u: string): string | undefined => {
  try {
    return new URL(u).hostname.replace(/^www\./, '')
  } catch {
    return undefined
  }
}

const fetchOnce = async (key: string, query: string): Promise<RandomFact | null> => {
  const resp = await fetch(TAVILY_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${key}`
    },
    body: JSON.stringify({
      query,
      max_results: 8,
      search_depth: 'advanced',
      include_answer: true,
      include_raw_content: false,
      include_images: false,
    })
  })

  if (!resp.ok) {
    console.error('[RandomFacts] Tavily error', resp.status, resp.statusText)
    return null
  }

  const data: { answer?: string; results?: Array<{ title: string; url: string; content: string; score: number; published_date?: string }> } = await resp.json()
  const items = (data.results || []).map(r => {
    const url = normalizeUrl(r.url)
    const domain = domainFromUrl(url)
    const snippet = r.content?.trim() || ''
    const verdictFromAnswer = (() => {
      const ans = (data.answer || '').toLowerCase()
      if (ans.includes('no')) return 'No' as const
      if (ans.includes('yes')) return 'Yes' as const
      return null
    })()

    const fallbackVerdict = verdictFromAnswer || deriveVerdict(data.answer) || deriveVerdict(snippet) || deriveVerdict(r.title)

    const mainText = (data.answer || snippet || '').trim()

    return {
      title: r.title || url,
      url,
      snippet: mainText.slice(0, 220) + (mainText.length > 220 ? '...' : ''),
      reliability: reliabilityFromDomain(domain),
      publisher: domain,
      publishedAt: r.published_date,
      source: 'tavily',
      verdict: fallbackVerdict,
      question: query,
      answer: mainText,
    }
  }).filter(r => r.snippet && r.title && r.url && r.verdict)

  if (items.length === 0) return null

  const pick = items[Math.floor(Math.random() * items.length)] as RandomFact
  return pick
}

export async function fetchRandomFact(): Promise<RandomFact | null> {
  const key = process.env.TAVILY_FACTS_API_KEY || process.env.TAVILY_API_KEY
  if (!key) {
    console.warn('[RandomFacts] Tavily key missing')
    return null
  }

  const prompts = shuffle(ALL_YES_NO_PROMPTS).slice(0, 5) // try up to 5 different yes/no claims

  for (const q of prompts) {
    try {
      const fact = await fetchOnce(key, q)
      if (fact) return fact
    } catch (err) {
      console.error('[RandomFacts] attempt failed', err)
    }
  }

  return null
}
