import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

// Base date: 2026-08-17 (today)
const TODAY = new Date('2026-08-17T07:00:00+07:00')
const d = (offsetDays: number, hour = 12, minute = 0) => {
  const dt = new Date(TODAY)
  dt.setDate(dt.getDate() + offsetDays)
  dt.setHours(hour, minute, 0, 0)
  return dt
}

async function main() {
  console.log('🏨 Seeding A Z Hotel Growth OS...')

  await prisma.hotelSetting.deleteMany()
  await prisma.marketingContent.deleteMany()
  await prisma.incident.deleteMany()
  await prisma.directBookingLead.deleteMany()
  await prisma.localRecommendation.deleteMany()
  await prisma.reviewRequest.deleteMany()
  await prisma.guestFeedback.deleteMany()
  await prisma.maintenanceIssue.deleteMany()
  await prisma.housekeepingTask.deleteMany()
  await prisma.serviceRequest.deleteMany()
  await prisma.stay.deleteMany()
  await prisma.room.deleteMany()
  await prisma.guest.deleteMany()
  await prisma.user.deleteMany()
  await prisma.hotel.deleteMany()

  // ── Hotel ──────────────────────────────────────────────────────────────────
  const hotel = await prisma.hotel.create({
    data: {
      name: 'A Z Hotel',
      slug: 'az-hotel-phnom-penh',
      tagline: 'Your Local Base in Phnom Penh',
      address: 'Street 19, Daun Penh',
      city: 'Phnom Penh',
      country: 'Cambodia',
      phone: '+855 23 999 888',
      email: 'hello@azhotel.com.kh',
      website: 'https://azhotel.com.kh',
      checkInTime: '14:00',
      checkOutTime: '12:00',
      wifiName: 'AZHotel_Guest',
      wifiPassword: 'welcome2AZ',
      currency: 'USD',
      timezone: 'Asia/Phnom_Penh',
    },
  })

  // ── Staff users ────────────────────────────────────────────────────────────
  await prisma.user.createMany({
    data: [
      { hotelId: hotel.id, name: 'Sophal Meas', email: 'manager@azhotel.com.kh', role: 'MANAGER', department: 'Management' },
      { hotelId: hotel.id, name: 'Dara Keo', email: 'front@azhotel.com.kh', role: 'STAFF', department: 'Front Desk' },
      { hotelId: hotel.id, name: 'Chantha Pov', email: 'hk@azhotel.com.kh', role: 'STAFF', department: 'Housekeeping' },
      { hotelId: hotel.id, name: 'Virak Srun', email: 'maintenance@azhotel.com.kh', role: 'STAFF', department: 'Maintenance' },
    ],
  })

  // ── Rooms (24 rooms, 4 floors) ─────────────────────────────────────────────
  const roomDefs = [
    // Floor 1 — Standard ($35)
    { number: '101', floor: 1, type: 'Standard', status: 'OCCUPIED', price: 35 },
    { number: '102', floor: 1, type: 'Standard', status: 'VACANT_CLEAN', price: 35 },
    { number: '103', floor: 1, type: 'Standard', status: 'OCCUPIED', price: 35 },
    { number: '104', floor: 1, type: 'Standard', status: 'VACANT_DIRTY', price: 35 },
    { number: '105', floor: 1, type: 'Standard', status: 'OCCUPIED', price: 35 },
    { number: '106', floor: 1, type: 'Standard', status: 'VACANT_CLEAN', price: 35 },
    // Floor 2 — Deluxe ($45)
    { number: '201', floor: 2, type: 'Deluxe', status: 'VACANT_CLEAN', price: 45 },
    { number: '202', floor: 2, type: 'Deluxe', status: 'OCCUPIED', price: 45 },
    { number: '203', floor: 2, type: 'Deluxe', status: 'VACANT_CLEAN', price: 45 },
    { number: '204', floor: 2, type: 'Deluxe', status: 'OCCUPIED', price: 45 },
    { number: '205', floor: 2, type: 'Deluxe', status: 'OCCUPIED', price: 45 },
    { number: '206', floor: 2, type: 'Deluxe', status: 'OUT_OF_SERVICE', price: 45 },
    // Floor 3 — Deluxe+ ($45)
    { number: '301', floor: 3, type: 'Deluxe', status: 'VACANT_CLEAN', price: 45 },
    { number: '302', floor: 3, type: 'Deluxe', status: 'OCCUPIED', price: 45 },
    { number: '303', floor: 3, type: 'Deluxe', status: 'VACANT_DIRTY', price: 45 },
    { number: '304', floor: 3, type: 'Deluxe', status: 'OCCUPIED', price: 45 },
    { number: '305', floor: 3, type: 'Deluxe', status: 'VACANT_CLEAN', price: 45 },
    { number: '306', floor: 3, type: 'Deluxe', status: 'VACANT_CLEAN', price: 45 },
    // Floor 4 — Superior ($55)
    { number: '401', floor: 4, type: 'Superior', status: 'OCCUPIED', price: 55 },
    { number: '402', floor: 4, type: 'Superior', status: 'VACANT_CLEAN', price: 55 },
    { number: '403', floor: 4, type: 'Superior', status: 'OCCUPIED', price: 55 },
    { number: '404', floor: 4, type: 'Superior', status: 'VACANT_CLEAN', price: 55 },
    { number: '405', floor: 4, type: 'Superior', status: 'INSPECTION', price: 55 },
    { number: '406', floor: 4, type: 'Superior', status: 'VACANT_CLEAN', price: 55 },
  ]

  const rooms: Record<string, string> = {}
  for (const r of roomDefs) {
    const room = await prisma.room.create({
      data: {
        hotelId: hotel.id,
        number: r.number,
        floor: r.floor,
        type: r.type,
        status: r.status,
        maxGuests: r.type === 'Superior' ? 3 : 2,
        pricePerNight: r.price,
      },
    })
    rooms[r.number] = room.id
  }

  // ── Guests ─────────────────────────────────────────────────────────────────
  const guestData = [
    { first: 'Chen', last: 'Wei', nationality: 'Chinese', lang: 'zh', repeat: false, notes: 'Travelling with partner Chen Mei. Interested in Royal Palace.' },
    { first: 'Thomas', last: 'Mitchell', nationality: 'British', lang: 'en', repeat: false, notes: 'Business traveller. Early riser, very tidy.' },
    { first: 'Arjun', last: 'Sharma', nationality: 'Indian', lang: 'en', repeat: false, notes: 'Solo food blogger. Vegetarian. Very enthusiastic about local cuisine.' },
    { first: 'Sarah', last: 'Park', nationality: 'American', lang: 'en', repeat: false, notes: 'Travelling with Michael Park. Honeymoon trip. Room should be prepared nicely.' },
    { first: 'Yuki', last: 'Tanaka', nationality: 'Japanese', lang: 'ja', repeat: false, notes: 'Solo traveller. Vegetarian. Quiet, considerate guest.' },
    { first: 'Diego', last: 'Hernandez', nationality: 'Mexican', lang: 'es', repeat: true, totalVisits: 2, notes: '2nd stay with us. Always books direct. Very positive about the hotel.' },
    { first: 'Emma', last: 'Wilson', nationality: 'Australian', lang: 'en', repeat: false, notes: 'Unhappy about AC issue in room 302. Recovery case — handle with care.' },
    { first: 'Nguyen Van', last: 'An', nationality: 'Vietnamese', lang: 'vi', repeat: true, totalVisits: 3, notes: 'Regular business guest. 3rd stay. Prefers quiet room. Late checkout often needed.' },
    { first: 'Robert', last: 'Blackwood', nationality: 'British', lang: 'en', repeat: true, totalVisits: 3, notes: 'Returning guest, 3rd visit with wife Helen. Knows the hotel well.' },
    { first: 'Sophie', last: 'Laurent', nationality: 'French', lang: 'fr', repeat: false, notes: 'Solo traveller, student. Interested in history sites.' },
  ]

  const guests: Record<string, string> = {}
  for (const g of guestData) {
    const guest = await prisma.guest.create({
      data: {
        hotelId: hotel.id,
        firstName: g.first,
        lastName: g.last,
        nationality: g.nationality,
        language: g.lang,
        isRepeat: g.repeat ?? false,
        totalVisits: g.totalVisits ?? 1,
        notes: g.notes,
      },
    })
    guests[`${g.first} ${g.last}`] = guest.id
  }

  // ── Stays ──────────────────────────────────────────────────────────────────
  const stayDefs = [
    { guest: 'Chen Wei', room: '101', checkIn: d(-2, 14), checkOut: d(2, 12), status: 'CHECKED_IN', adults: 2, source: 'booking.com', rate: 35 },
    { guest: 'Thomas Mitchell', room: '103', checkIn: d(-3, 14), checkOut: d(0, 12), status: 'CHECKED_IN', adults: 1, source: 'agoda', rate: 35 },
    { guest: 'Arjun Sharma', room: '105', checkIn: d(-1, 14), checkOut: d(5, 12), status: 'CHECKED_IN', adults: 1, source: 'booking.com', rate: 35 },
    { guest: 'Sarah Park', room: '202', checkIn: d(0, 10), checkOut: d(3, 12), status: 'CHECKED_IN', adults: 2, source: 'direct', rate: 45 },
    { guest: 'Yuki Tanaka', room: '204', checkIn: d(0, 15), checkOut: d(4, 12), status: 'CHECKED_IN', adults: 1, source: 'agoda', rate: 45 },
    { guest: 'Diego Hernandez', room: '205', checkIn: d(-4, 14), checkOut: d(1, 12), status: 'CHECKED_IN', adults: 1, source: 'direct', rate: 45 },
    { guest: 'Emma Wilson', room: '302', checkIn: d(-1, 14), checkOut: d(2, 12), status: 'CHECKED_IN', adults: 1, source: 'booking.com', rate: 45 },
    { guest: 'Nguyen Van An', room: '304', checkIn: d(-7, 14), checkOut: d(1, 12), status: 'CHECKED_IN', adults: 1, source: 'direct', rate: 45 },
    { guest: 'Robert Blackwood', room: '401', checkIn: d(0, 14), checkOut: d(3, 12), status: 'CHECKED_IN', adults: 2, source: 'direct', rate: 55 },
    { guest: 'Sophie Laurent', room: '403', checkIn: d(-2, 14), checkOut: d(1, 12), status: 'CHECKED_IN', adults: 1, source: 'booking.com', rate: 45 },
  ]

  const stays: Record<string, string> = {}
  for (const s of stayDefs) {
    const stay = await prisma.stay.create({
      data: {
        hotelId: hotel.id,
        guestId: guests[s.guest],
        roomId: rooms[s.room],
        checkIn: s.checkIn,
        checkOut: s.checkOut,
        status: s.status,
        adults: s.adults,
        children: 0,
        source: s.source,
        ratePerNight: s.rate,
      },
    })
    stays[s.guest] = stay.id
  }

  // ── Service Requests ───────────────────────────────────────────────────────
  await prisma.serviceRequest.createMany({
    data: [
      {
        hotelId: hotel.id,
        stayId: stays['Emma Wilson'],
        guestId: guests['Emma Wilson'],
        roomId: rooms['302'],
        type: 'maintenance',
        category: 'Air Conditioning',
        description: 'AC unit not cooling properly. Room is uncomfortably warm. Guest reported multiple times.',
        priority: 'HIGH',
        status: 'IN_PROGRESS',
        assignedTo: 'Virak Srun',
        notes: 'Technician checked — refrigerant low. Parts ordered. ETA: tomorrow morning.',
        createdAt: d(-1, 16, 30),
        updatedAt: d(-1, 17, 15),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Emma Wilson'],
        guestId: guests['Emma Wilson'],
        roomId: rooms['302'],
        type: 'transport',
        category: 'Airport Transfer',
        description: 'Guest needs airport pickup on Aug 19 at 10:00am. Departure flight 13:00.',
        priority: 'NORMAL',
        status: 'NEW',
        createdAt: d(0, 8, 15),
        updatedAt: d(0, 8, 15),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Nguyen Van An'],
        guestId: guests['Nguyen Van An'],
        roomId: rooms['304'],
        type: 'request',
        category: 'Late Checkout',
        description: 'Requesting late checkout until 14:00 on Aug 18. Business meeting in the morning.',
        priority: 'NORMAL',
        status: 'NEW',
        createdAt: d(0, 7, 0),
        updatedAt: d(0, 7, 0),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Chen Wei'],
        guestId: guests['Chen Wei'],
        roomId: rooms['101'],
        type: 'amenity',
        category: 'Housekeeping',
        description: 'Extra blanket requested for the room.',
        priority: 'LOW',
        status: 'COMPLETED',
        assignedTo: 'Chantha Pov',
        resolvedAt: d(-1, 18, 0),
        createdAt: d(-1, 15, 0),
        updatedAt: d(-1, 18, 0),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Arjun Sharma'],
        guestId: guests['Arjun Sharma'],
        roomId: rooms['105'],
        type: 'concierge',
        category: 'Dining',
        description: 'Guest asking for vegetarian restaurant recommendations near the hotel.',
        priority: 'NORMAL',
        status: 'COMPLETED',
        assignedTo: 'Dara Keo',
        notes: 'Recommended Friends Restaurant and Romdeng. Provided map.',
        resolvedAt: d(0, 8, 45),
        createdAt: d(0, 8, 0),
        updatedAt: d(0, 8, 45),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Diego Hernandez'],
        guestId: guests['Diego Hernandez'],
        roomId: rooms['205'],
        type: 'amenity',
        category: 'Housekeeping',
        description: 'Extra towels needed.',
        priority: 'NORMAL',
        status: 'COMPLETED',
        assignedTo: 'Chantha Pov',
        resolvedAt: d(-1, 11, 30),
        createdAt: d(-1, 10, 0),
        updatedAt: d(-1, 11, 30),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Sarah Park'],
        guestId: guests['Sarah Park'],
        roomId: rooms['202'],
        type: 'request',
        category: 'Information',
        description: 'Asking for best spots for sunset photos and a romantic dinner tonight.',
        priority: 'NORMAL',
        status: 'NEW',
        createdAt: d(0, 11, 30),
        updatedAt: d(0, 11, 30),
      },
    ],
  })

  // ── Housekeeping Tasks ─────────────────────────────────────────────────────
  await prisma.housekeepingTask.createMany({
    data: [
      {
        hotelId: hotel.id,
        roomId: rooms['104'],
        type: 'FULL_CLEAN',
        status: 'PENDING',
        priority: 'HIGH',
        notes: 'Previous guest checked out this morning. Full turnover required before next booking.',
        scheduledFor: d(0, 10),
        createdAt: d(0, 9),
        updatedAt: d(0, 9),
      },
      {
        hotelId: hotel.id,
        roomId: rooms['103'],
        type: 'CHECKOUT_CLEAN',
        status: 'PENDING',
        priority: 'HIGH',
        assignedTo: 'Chantha Pov',
        notes: 'Thomas Mitchell checking out. Checkout clean required.',
        scheduledFor: d(0, 12),
        createdAt: d(0, 7),
        updatedAt: d(0, 7),
      },
      {
        hotelId: hotel.id,
        roomId: rooms['303'],
        type: 'FULL_CLEAN',
        status: 'IN_PROGRESS',
        priority: 'NORMAL',
        assignedTo: 'Chantha Pov',
        notes: 'Room vacated yesterday. In progress.',
        scheduledFor: d(0, 9),
        createdAt: d(-1, 15),
        updatedAt: d(0, 9, 30),
      },
      {
        hotelId: hotel.id,
        roomId: rooms['202'],
        type: 'WELCOME_SETUP',
        status: 'COMPLETED',
        priority: 'HIGH',
        assignedTo: 'Chantha Pov',
        notes: 'Honeymoon setup: extra towels, turned down bed, welcome note.',
        completedAt: d(0, 9, 30),
        createdAt: d(0, 7),
        updatedAt: d(0, 9, 30),
      },
      {
        hotelId: hotel.id,
        roomId: rooms['401'],
        type: 'WELCOME_SETUP',
        status: 'PENDING',
        priority: 'HIGH',
        assignedTo: 'Chantha Pov',
        notes: 'Returning guests (3rd visit). Welcome note from manager.',
        scheduledFor: d(0, 13),
        createdAt: d(0, 7),
        updatedAt: d(0, 7),
      },
      {
        hotelId: hotel.id,
        roomId: rooms['302'],
        type: 'DAILY_CLEAN',
        status: 'PENDING',
        priority: 'NORMAL',
        notes: 'Note: confirm AC repair complete before cleaning.',
        guestInstruction: 'CLEAN_NOW',
        scheduledFor: d(0, 10),
        createdAt: d(0, 7),
        updatedAt: d(0, 7),
      },
    ],
  })

  // ── Maintenance Issues ─────────────────────────────────────────────────────
  await prisma.maintenanceIssue.createMany({
    data: [
      {
        hotelId: hotel.id,
        roomId: rooms['302'],
        category: 'ac',
        description: 'AC unit insufficient cooling. Refrigerant low. Guest complaint — recovery case.',
        severity: 'HIGH',
        status: 'IN_PROGRESS',
        reportedBy: 'Emma Wilson (guest)',
        assignedTo: 'Virak Srun',
        notes: 'Parts ordered. Scheduled completion tomorrow morning. Offered fan in interim.',
        isRecurring: false,
        createdAt: d(-1, 16),
        updatedAt: d(-1, 17),
      },
      {
        hotelId: hotel.id,
        roomId: rooms['206'],
        category: 'ac',
        description: 'AC complete failure. Room taken out of service until repaired.',
        severity: 'CRITICAL',
        status: 'OPEN',
        reportedBy: 'Dara Keo',
        assignedTo: 'Virak Srun',
        notes: 'AC unit total failure. Technician needed. Room blocked until resolved.',
        isRecurring: true,
        createdAt: d(-2, 9),
        updatedAt: d(-2, 10),
      },
      {
        hotelId: hotel.id,
        roomId: null,
        category: 'lighting',
        description: 'Fluorescent light flickering in Floor 2 corridor near stairs.',
        severity: 'LOW',
        status: 'OPEN',
        reportedBy: 'Chantha Pov',
        assignedTo: '',
        notes: 'Not urgent but should be fixed this week.',
        createdAt: d(-1, 14),
        updatedAt: d(-1, 14),
      },
      {
        hotelId: hotel.id,
        roomId: rooms['103'],
        category: 'plumbing',
        description: 'Bathroom drain running slowly.',
        severity: 'MEDIUM',
        status: 'RESOLVED',
        reportedBy: 'Thomas Mitchell (guest)',
        assignedTo: 'Virak Srun',
        notes: 'Drain cleared. Resolved same day.',
        resolvedAt: d(-2, 16),
        createdAt: d(-2, 10),
        updatedAt: d(-2, 16),
      },
    ],
  })

  // ── Guest Feedback ─────────────────────────────────────────────────────────
  const feedback = await prisma.guestFeedback.createMany({
    data: [
      {
        hotelId: hotel.id,
        stayId: stays['Chen Wei'],
        guestId: guests['Chen Wei'],
        sentiment: 'POSITIVE',
        rating: 5,
        comment: 'Very friendly staff and excellent location. The tips for Royal Palace were spot on. Will definitely recommend to friends.',
        category: 'Staff & Location',
        isResolved: true,
        createdAt: d(-1, 20),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Emma Wilson'],
        guestId: guests['Emma Wilson'],
        sentiment: 'NEGATIVE',
        rating: 2,
        comment: 'The room is very hot — the air conditioning is not working properly. I have reported it but it is still not fixed. Very uncomfortable.',
        category: 'Room Condition',
        isResolved: false,
        isRecoveryCase: true,
        recoveryNotes: 'Maintenance on it. Offer room credit and apology note.',
        createdAt: d(0, 9),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Thomas Mitchell'],
        guestId: guests['Thomas Mitchell'],
        sentiment: 'POSITIVE',
        rating: 4,
        comment: 'Clean, efficient, excellent location for business. Good value.',
        category: 'Value & Cleanliness',
        isResolved: true,
        createdAt: d(0, 8),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Diego Hernandez'],
        guestId: guests['Diego Hernandez'],
        sentiment: 'POSITIVE',
        rating: 5,
        comment: 'Best value in Phnom Penh. The team is so friendly and knowledgeable about the city. My second stay and I am already planning a third.',
        category: 'Overall Experience',
        isResolved: true,
        createdAt: d(-1, 19),
      },
      {
        hotelId: hotel.id,
        stayId: stays['Nguyen Van An'],
        guestId: guests['Nguyen Van An'],
        sentiment: 'NEUTRAL',
        rating: 3,
        comment: 'Good for work stays. Basic but functional. Late checkout would be helpful.',
        category: 'Business Facilities',
        isResolved: true,
        createdAt: d(0, 7, 30),
      },
    ],
  })

  // ── Review Requests ────────────────────────────────────────────────────────
  await prisma.reviewRequest.createMany({
    data: [
      {
        hotelId: hotel.id,
        guestId: guests['Diego Hernandez'],
        stayId: stays['Diego Hernandez'],
        platform: 'google',
        status: 'CANDIDATE',
        createdAt: d(0, 9),
      },
      {
        hotelId: hotel.id,
        guestId: guests['Thomas Mitchell'],
        stayId: stays['Thomas Mitchell'],
        platform: 'booking.com',
        status: 'CANDIDATE',
        createdAt: d(0, 8),
      },
      {
        hotelId: hotel.id,
        guestId: guests['Chen Wei'],
        stayId: stays['Chen Wei'],
        platform: 'google',
        status: 'CANDIDATE',
        createdAt: d(-1, 20),
      },
    ],
  })

  // ── Direct Booking Leads ───────────────────────────────────────────────────
  await prisma.directBookingLead.createMany({
    data: [
      {
        hotelId: hotel.id,
        guestId: guests['Thomas Mitchell'],
        name: 'Thomas Mitchell',
        email: 'thomas.mitchell@example.com',
        checkIn: new Date('2026-09-08'),
        checkOut: new Date('2026-09-13'),
        adults: 1,
        message: 'Would like to return for another business trip in September. Same room if possible.',
        status: 'NEW',
        source: 'repeat',
        createdAt: d(0, 8),
        updatedAt: d(0, 8),
      },
      {
        hotelId: hotel.id,
        guestId: guests['Diego Hernandez'],
        name: 'Diego Hernandez',
        email: 'diego.hernandez@example.com',
        checkIn: new Date('2026-11-12'),
        checkOut: new Date('2026-11-26'),
        adults: 1,
        message: 'Planning a two-week stay in November. Do you have a long-stay rate? Keen to come back!',
        status: 'NEW',
        source: 'repeat',
        createdAt: d(-1, 21),
        updatedAt: d(-1, 21),
      },
      {
        hotelId: hotel.id,
        guestId: guests['Robert Blackwood'],
        name: 'Robert & Helen Blackwood',
        email: 'r.blackwood@example.com',
        checkIn: new Date('2027-02-10'),
        checkOut: new Date('2027-02-17'),
        adults: 2,
        message: 'Already booked this visit. Want to tentatively reserve same dates next February.',
        status: 'NEW',
        source: 'repeat',
        createdAt: d(-30),
        updatedAt: d(-30),
      },
    ],
  })

  // ── Local Recommendations ──────────────────────────────────────────────────
  await prisma.localRecommendation.createMany({
    data: [
      // EAT
      { hotelId: hotel.id, category: 'eat', name: 'Friends The Restaurant', description: 'International and Khmer menu run by a social enterprise that trains at-risk youth. Genuinely excellent food and a great story.', distance: '10 min walk', transport: 'Walk via Sothearos Blvd', address: '215 Sisowath Quay', hours: '11am–10pm', priceRange: '$$', hotelNote: 'One of our top picks — we always send guests here.', sortOrder: 1 },
      { hotelId: hotel.id, category: 'eat', name: 'Romdeng Restaurant', description: 'Traditional Cambodian cuisine in a beautiful colonial villa. Famous for the tarantula dish if you dare. Bookings recommended.', distance: '8 min walk', transport: 'Walk or tuk-tuk', address: '74 Street 174', hours: '11am–9:30pm', priceRange: '$$', hotelNote: 'Best Khmer food close to the hotel.', sortOrder: 2 },
      { hotelId: hotel.id, category: 'eat', name: 'The Lost Room', description: 'Relaxed international bistro with good burgers, salads and daily specials. Good for a quiet dinner.', distance: '3 min walk', transport: 'Walk', hours: '11am–11pm', priceRange: '$$', hotelNote: 'Staff favourite for a quick dinner.', sortOrder: 3 },
      { hotelId: hotel.id, category: 'eat', name: 'Street 278 Noodle Stalls', description: 'Early morning noodle soup — kuy teav — from street vendors. Proper local breakfast for around $1.50. Go before 9am.', distance: '2 min walk', transport: 'Walk', hours: '6am–10am', priceRange: '$', hotelNote: 'The real Phnom Penh breakfast. We go here every morning.', sortOrder: 4 },
      { hotelId: hotel.id, category: 'eat', name: 'Mama Restaurant', description: 'No-frills Khmer home cooking. Cheap, cheerful, and delicious. Order the amok.', distance: '5 min walk', transport: 'Walk', hours: '7am–9pm', priceRange: '$', hotelNote: "Our team's regular lunch spot.", sortOrder: 5 },
      // COFFEE
      { hotelId: hotel.id, category: 'coffee', name: 'Brown Coffee & Bakery', description: 'Cambodia\'s best local coffee chain. Reliable quality, air-conditioned, great for working. Excellent cold brew.', distance: '5 min walk', transport: 'Walk', hours: '7am–9pm', priceRange: '$', hotelNote: 'Consistent quality every time.', sortOrder: 1 },
      { hotelId: hotel.id, category: 'coffee', name: 'Java Arts', description: 'Specialty coffee shop with rotating single-origins. Also an art gallery. Great for a longer sit.', distance: '7 min walk', transport: 'Walk', hours: '8am–7pm', priceRange: '$$', hotelNote: 'Best specialty coffee in the neighbourhood.', sortOrder: 2 },
      { hotelId: hotel.id, category: 'coffee', name: 'Daughters of Cambodia Café', description: 'Coffee shop run by a charity supporting trafficking survivors. Genuinely good flat whites and iced coffees.', distance: '4 min walk', transport: 'Walk', hours: '8am–5pm', priceRange: '$', hotelNote: 'A great cause and great coffee.', sortOrder: 3 },
      { hotelId: hotel.id, category: 'coffee', name: 'Café Fresco', description: 'Casual café with reliable WiFi. Good for remote workers. Simple but solid espresso drinks.', distance: '3 min walk', transport: 'Walk', hours: '7am–9pm', priceRange: '$', sortOrder: 4 },
      // DRINKS
      { hotelId: hotel.id, category: 'drinks', name: 'FCC Rooftop Bar', description: 'The Foreign Correspondents Club — historic riverside bar with a spectacular terrace. Perfect for sunset cocktails.', distance: '12 min walk', transport: 'Walk along the river', address: '363 Sisowath Quay', hours: '7am–midnight', priceRange: '$$', hotelNote: 'Iconic. Go for sunset — it is worth the walk.', sortOrder: 1 },
      { hotelId: hotel.id, category: 'drinks', name: 'The Envoy', description: 'Craft beer and cocktails in a relaxed setting. Good selection of Southeast Asian beers and local labels.', distance: '8 min walk', transport: 'Walk', hours: '4pm–midnight', priceRange: '$$', sortOrder: 2 },
      { hotelId: hotel.id, category: 'drinks', name: 'Bong Bong Bar', description: 'Lively local bar with a creative cocktail menu. Popular with expats and long-term visitors.', distance: '8 min walk', transport: 'Walk or tuk-tuk', hours: '5pm–1am', priceRange: '$$', sortOrder: 3 },
      // ESSENTIALS
      { hotelId: hotel.id, category: 'essentials', name: 'Lucky Lucky Market', description: 'Supermarket 3 minutes from the hotel. Water, snacks, toiletries, alcohol, local snacks. Open late.', distance: '3 min walk', transport: 'Walk', hours: '7am–10pm', priceRange: '$', hotelNote: 'Your first stop for anything you need.', sortOrder: 1 },
      { hotelId: hotel.id, category: 'essentials', name: 'AEON Mall', description: 'Air-conditioned mall with a large supermarket, food court, pharmacy, ATMs and international brands.', distance: '5 min tuk-tuk', transport: 'Tuk-tuk ~$2', hours: '9am–10pm', priceRange: '$-$$', sortOrder: 2 },
      // PHARMACY
      { hotelId: hotel.id, category: 'pharmacy', name: 'U-Care Pharmacy', description: 'Reliable chain pharmacy with English-speaking staff. Well-stocked with international brands.', distance: '4 min walk', transport: 'Walk', hours: '8am–9pm', priceRange: '$', hotelNote: 'Our recommended pharmacy — staff speak English.', sortOrder: 1 },
      { hotelId: hotel.id, category: 'pharmacy', name: 'Pharmacie de la Gare', description: 'Basic pharmacy with French and Khmer staff. Cheaper for simple supplies.', distance: '2 min walk', transport: 'Walk', hours: '8am–7pm', priceRange: '$', sortOrder: 2 },
      // SIM
      { hotelId: hotel.id, category: 'sim', name: 'Smart or Cellcard SIM', description: 'Buy a local data SIM at Lucky Lucky Market (3 min walk) or at AEON Mall. Around $2–5 for a tourist SIM with 5–10GB data. Works well everywhere in the city.', distance: '3 min walk (Lucky Lucky)', transport: 'Walk', hours: 'Market hours', priceRange: '$', hotelNote: 'We recommend Smart for city coverage. Bring your passport.', sortOrder: 1 },
      // LAUNDRY
      { hotelId: hotel.id, category: 'laundry', name: 'Same-Day Laundry — Street 19', description: 'Laundry shop 2 minutes from the hotel. Same-day service if dropped off before 10am. Around $1–1.50 per kg.', distance: '2 min walk', transport: 'Walk', hours: '7am–7pm', priceRange: '$', hotelNote: 'Quick, cheap, reliable. We use them ourselves.', sortOrder: 1 },
      // TRANSPORT
      { hotelId: hotel.id, category: 'transport', name: 'Grab App', description: 'Ride-hailing app covering Phnom Penh. Fixed fares, no negotiation. The most reliable option. Download before you travel.', distance: '-', transport: 'App-based', priceRange: '$-$$', hotelNote: 'Download Grab before you arrive. Most reliable option in the city.', sortOrder: 1 },
      { hotelId: hotel.id, category: 'transport', name: 'PassApp', description: 'Cambodian alternative to Grab. Often slightly cheaper. Good coverage across the city.', distance: '-', transport: 'App-based', priceRange: '$', sortOrder: 2 },
      { hotelId: hotel.id, category: 'transport', name: 'Airport Transfer', description: 'Book through reception for a flat-rate transfer to/from Phnom Penh International Airport. $12 one way, air-conditioned car.', distance: '25 min drive', transport: 'Hotel car', priceRange: '$$', hotelNote: 'Book at reception at least 2 hours ahead.', sortOrder: 3 },
      { hotelId: hotel.id, category: 'transport', name: 'Hotel Tuk-Tuk', description: 'Ask at reception for our recommended tuk-tuk drivers. City centre destinations typically $2–4. Airport $8–10.', distance: 'City-wide', transport: 'Tuk-tuk', priceRange: '$-$$', hotelNote: 'Our drivers know the city. Ask reception to arrange.', sortOrder: 4 },
      // ATTRACTIONS
      { hotelId: hotel.id, category: 'attractions', name: 'Royal Palace & Silver Pagoda', description: 'The most important site in Phnom Penh. Stunning Khmer architecture, sacred grounds and the Silver Pagoda floor. Allow 90 minutes.', distance: '12 min tuk-tuk', transport: 'Tuk-tuk ~$3', hours: '7:30–11am, 2–5pm (closed Fri PM)', priceRange: '$10', hotelNote: "Don't miss it — go in the morning before 10am to avoid the heat.", sortOrder: 1 },
      { hotelId: hotel.id, category: 'attractions', name: 'National Museum of Cambodia', description: 'World-class collection of Khmer art and sculpture, housed in a beautiful traditional building. One of the best museums in Southeast Asia.', distance: '10 min walk', transport: 'Walk or tuk-tuk', hours: '8am–5pm daily', priceRange: '$5', sortOrder: 2 },
      { hotelId: hotel.id, category: 'attractions', name: 'Tuol Sleng Genocide Museum (S-21)', description: 'Former Khmer Rouge prison. Sobering and important. A significant part of understanding Cambodian history. Allow 2 hours.', distance: '20 min tuk-tuk', transport: 'Tuk-tuk ~$4', hours: '8am–5pm daily', priceRange: '$5', sortOrder: 3 },
      { hotelId: hotel.id, category: 'attractions', name: 'Phnom Penh Riverside Promenade', description: 'The riverside walk along Sisowath Quay at sunset. Free, beautiful, and full of local life. Great for an evening stroll.', distance: '12 min walk', transport: 'Walk', hours: 'Always open', priceRange: 'Free', hotelNote: 'Best at sunset. Walk from the hotel — it is a pleasant route.', sortOrder: 4 },
      { hotelId: hotel.id, category: 'attractions', name: 'Central Market (Phsar Thmei)', description: 'Beautiful 1937 art deco market with jewellery, clothing, local food and souvenirs. Good for gifts. Bargain confidently.', distance: '15 min walk', transport: 'Walk or tuk-tuk', hours: '7am–5pm', priceRange: 'Free entry', sortOrder: 5 },
      // LATE NIGHT
      { hotelId: hotel.id, category: 'late_night', name: 'Street 278 Bar Strip', description: 'A line of bars popular with travellers and expats. Lively from 9pm onwards. Walkable from the hotel.', distance: '10 min walk', transport: 'Walk', hours: '9pm–2am+', priceRange: '$-$$', sortOrder: 1 },
      { hotelId: hotel.id, category: 'late_night', name: 'FCC Riverside (Late)', description: 'The FCC Riverside terrace stays open late and is the most civilised late-night spot in the city. Cocktails with a river view.', distance: '12 min walk', transport: 'Walk or tuk-tuk', hours: 'Until midnight+', priceRange: '$$', sortOrder: 2 },
      // LOCAL TIPS
      { hotelId: hotel.id, category: 'tips', name: 'Royal Palace — go early', description: 'The best time to visit is 8–10am. The light is beautiful, it is cooler, and you will beat the tour groups.', sortOrder: 1 },
      { hotelId: hotel.id, category: 'tips', name: 'Money & ATMs', description: 'USD is accepted everywhere. You will receive Riel (KHR) as change, which is normal. ATMs on Street 214 (5 min walk) dispense USD. Riel is only used for small change.', sortOrder: 2 },
      { hotelId: hotel.id, category: 'tips', name: 'Drinking water', description: 'Drink bottled water only. Free refills of cold bottled water are available at hotel reception all day. Do not drink tap water.', sortOrder: 3 },
      { hotelId: hotel.id, category: 'tips', name: 'Tuk-tuk fares', description: '$2–4 is fair for most city-centre destinations. To the Royal Palace: $3–4. Agree the price before you get in. The apps (Grab, PassApp) show fixed fares and are often easiest.', sortOrder: 4 },
      { hotelId: hotel.id, category: 'tips', name: 'Weather & umbrellas', description: 'Rainy season runs June–November. Rain is usually short and heavy in the afternoon. Hotel has umbrellas to borrow — ask at reception.', sortOrder: 5 },
    ],
  })

  // ── Incidents ──────────────────────────────────────────────────────────────
  await prisma.incident.create({
    data: {
      hotelId: hotel.id,
      type: 'complaint',
      severity: 'MEDIUM',
      description: 'Guest in Room 302 (Emma Wilson) made formal complaint about AC not working. Guest is unhappy and considering leaving a negative review.',
      roomNumber: '302',
      guestName: 'Emma Wilson',
      actionTaken: 'Maintenance assigned. Interim fan provided. Apology from manager delivered. Monitoring situation.',
      owner: 'Sophal Meas',
      isResolved: false,
      createdAt: d(-1, 17),
    },
  })

  // ── Marketing Content ──────────────────────────────────────────────────────
  await prisma.marketingContent.createMany({
    data: [
      {
        hotelId: hotel.id,
        type: 'video_concept',
        platform: 'instagram',
        title: '3 Coffee Shops Within 10 Minutes',
        content: '20-second reel: Walk from hotel → Brown Coffee (morning cold brew shot) → Daughters of Cambodia (flat white + mission story) → Java Arts (pour-over, gallery wall). Caption: "Your morning in Phnom Penh starts here. Three great cafés, all within 10 minutes of A Z Hotel."',
        status: 'idea',
      },
      {
        hotelId: hotel.id,
        type: 'post_idea',
        platform: 'instagram',
        title: 'Your First Day in Phnom Penh',
        content: 'Carousel post: Frame 1: "Just landed? Here\'s your first day." Frame 2: Morning — kuy teav noodles on Street 278. Frame 3: Midday — Royal Palace (go before it gets hot). Frame 4: Afternoon — National Museum. Frame 5: Sunset — FCC Riverside terrace. Frame 6: "Base yourself at A Z Hotel and we\'ll help with the rest."',
        status: 'drafted',
      },
      {
        hotelId: hotel.id,
        type: 'campaign',
        platform: 'facebook',
        title: 'Why We Started A Z Hotel',
        content: 'Brand story post: "We built A Z Hotel because Phnom Penh deserves a hotel that feels genuinely local — not a chain, not a hostel. A place where the team knows the city, the rooms are clean and calm, and you leave knowing you actually experienced somewhere real. Your local base." — The A Z Team',
        status: 'idea',
      },
      {
        hotelId: hotel.id,
        type: 'video_concept',
        platform: 'tiktok',
        title: 'Phnom Penh by Tuk-Tuk',
        content: '30-second concept: Follow a guest\'s tuk-tuk journey from A Z Hotel through riverside, past Royal Palace, to Central Market. Voiceover: "Five places worth visiting in Phnom Penh. Your hotel is the starting point." Hotel logo at end.',
        status: 'idea',
      },
      {
        hotelId: hotel.id,
        type: 'caption',
        platform: 'instagram',
        title: 'Guest Story — Diego\'s Return Visit',
        content: '"We love it when guests come back. Diego just completed his second stay with us. \'Best value in Phnom Penh. The team knows the city better than any guidebook.\' See you again in November, Diego." [Room/lobby photo]',
        status: 'drafted',
      },
    ],
  })

  // ── Hotel Settings ─────────────────────────────────────────────────────────
  await prisma.hotelSetting.createMany({
    data: [
      { hotelId: hotel.id, key: 'google_rating', value: '4.2' },
      { hotelId: hotel.id, key: 'google_review_count', value: '184' },
      { hotelId: hotel.id, key: 'booking_rating', value: '8.1' },
      { hotelId: hotel.id, key: 'booking_review_count', value: '312' },
      { hotelId: hotel.id, key: 'tripadvisor_rating', value: '4.0' },
      { hotelId: hotel.id, key: 'tripadvisor_review_count', value: '97' },
      { hotelId: hotel.id, key: 'total_rooms', value: '24' },
      { hotelId: hotel.id, key: 'whatsapp_number', value: '+85523999888' },
      { hotelId: hotel.id, key: 'emergency_contact', value: '+855 23 999 888' },
      { hotelId: hotel.id, key: 'emergency_procedure_url', value: '' },
    ],
  })

  console.log('✅ A Z Hotel seeded successfully!')
  console.log('   24 rooms · 10 guests · 10 stays · 7 requests · 6 housekeeping tasks · 4 maintenance issues')
  console.log('   5 feedback records · 3 review candidates · 3 direct leads · 31 local recommendations')
  console.log('')
  console.log('🌐 Open http://localhost:3000 to see the Hotel Growth OS')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(() => prisma.$disconnect())
